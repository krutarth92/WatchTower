# Private Ubuntu EC2 staging deployment

Status: Task 16 non-production baseline, 2026-09-29.

## Approved target pattern

The V1 deployment baseline is one private Ubuntu EC2 host with Docker Engine and
the Compose plugin. One image runs three roles: a one-shot Alembic migrator, the
FastAPI service, and the Dramatiq worker. Compose also runs PostgreSQL 17 with
pgvector and Redis 7 on an internal Docker network. A named volume stores raw
objects for the single worker host.

The API publishes only to `127.0.0.1:8000` on the EC2 host through a dedicated
Docker ingress bridge. Reach it through an SSH tunnel during staging validation.
PostgreSQL and Redis attach only to the internal backend network. Do not add an
internet-facing security group rule. This pattern is for private non-production
staging; it is not the approved production architecture and does not satisfy the
release gates in `docs/security/threat-model.md`.

```text
administrator -> SSH -> EC2 loopback:8000 -> API container
                                      |-> internal PostgreSQL
                                      |-> internal Redis
worker -> internal PostgreSQL/Redis + outbound fixed ATT&CK HTTPS endpoint
worker -> named single-host raw-storage volume
```

## Host preparation

Use a supported Ubuntu LTS image, encrypted EBS, an instance role with only the
permissions actually required, and a security group allowing SSH only from the
administrative network. Install Docker Engine, the Compose plugin, Git, and
`flock`. Enable OS security updates and central host/container logs.

Create `/opt/watchtower` as a Git checkout owned by the deployment account. Copy
`.env.deploy.example` to `/opt/watchtower/.env.deploy`, set mode `0600`, and
replace every placeholder. Never commit or paste that file into CI logs.

The example uses local Docker volumes. Before production, replace raw storage
with an approved private S3-compatible `ObjectStore` implementation and decide
retention, encryption, backup, and access policy. A multi-host worker deployment
must not use this local volume.

## Configuration

`.env.deploy.example` is the complete staging template. The important values are:

| Variable | Purpose |
| --- | --- |
| `WATCHTOWER_IMAGE_TAG` | Immutable Git SHA image tag selected by deployment |
| `WATCHTOWER_BIND_PORT` | Host loopback port; defaults to 8000 |
| `POSTGRES_*` | Initial staging database and container credentials |
| `WATCHTOWER_DATABASE_URL` | Runtime URL using Compose host `postgres`; URL-encode its password |
| `WATCHTOWER_REDIS_URL` | Runtime URL using Compose host `redis` |
| `WATCHTOWER_OPERATOR_TOKEN` | Random staging token of at least 32 characters |
| `WATCHTOWER_RAW_STORAGE_PATH` | `/var/lib/watchtower/raw` inside the worker |
| `WATCHTOWER_ENVIRONMENT` | `staging` |

All other application variables and bounds are described in `SETUP.md`. GitHub
contains no deployment values. The `staging` GitHub Environment must define:

- `STAGING_SSH_HOST`
- `STAGING_SSH_USER`
- `STAGING_SSH_PRIVATE_KEY`
- `STAGING_SSH_KNOWN_HOSTS`, captured through a trusted provisioning channel

Configure required reviewers on that environment. Do not use `ssh-keyscan` at
deployment time because accepting a newly observed key would remove host
identity verification.

## First deployment

From `/opt/watchtower` on the EC2 host:

```bash
export WATCHTOWER_IMAGE_TAG="$(git rev-parse HEAD)"
docker compose --env-file .env.deploy -f compose.deploy.yaml config --quiet
docker compose --env-file .env.deploy -f compose.deploy.yaml build api
docker compose --env-file .env.deploy -f compose.deploy.yaml up -d --wait postgres redis
docker compose --env-file .env.deploy -f compose.deploy.yaml run --rm migrate
docker compose --env-file .env.deploy -f compose.deploy.yaml up -d --no-deps --wait api worker
docker compose --env-file .env.deploy -f compose.deploy.yaml ps
```

Open an SSH tunnel from the administrator workstation:

```bash
ssh -L 8000:127.0.0.1:8000 DEPLOY_USER@EC2_HOST
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/ready
```

`/health` proves the process responds. `/ready` also proves database
connectivity. Confirm the applied migration with the same immutable image:

```bash
docker compose --env-file .env.deploy -f compose.deploy.yaml run --rm migrate \
  alembic current
```

The worker has no public port. Confirm its running state and review structured
logs without printing its environment:

```bash
docker compose --env-file .env.deploy -f compose.deploy.yaml ps worker
docker compose --env-file .env.deploy -f compose.deploy.yaml logs --tail 100 api worker
```

## GitHub deployment flow

`.github/workflows/deploy-staging.yml` runs only through `workflow_dispatch` and
requires the literal confirmation `deploy-staging`. It uses the protected
`staging` environment and sends the checked-out full commit SHA to
`scripts/deploy_staging.sh` over pinned-host SSH. The server script:

1. locks deployment to one process,
2. fetches and checks out the exact commit,
3. validates Compose and builds the SHA-tagged image,
4. starts PostgreSQL and Redis and waits for health,
5. applies Alembic migrations once,
6. replaces API and worker and waits for readiness,
7. records current/previous image SHAs.

There is no push-triggered deployment and no production environment. Creation
of this workflow does not deploy anything. A human must dispatch it and satisfy
the staging environment protection rules.

## Migration and rollback policy

Review every Alembic revision before deployment. Additive/reversible migrations
may run through the one-shot service. A destructive or long-locking migration
requires a database backup, measured rehearsal, maintenance plan, and explicit
human approval. Never add automatic `alembic downgrade` to deployment.

If the new API or worker fails readiness, the staging script attempts to restore
the previous SHA-tagged application image. The database remains at the new
schema. If no usable previous image exists or rollback fails, the script stops
the API and worker rather than leaving a failed release running. Application
rollback is safe only when the previous image is compatible with the new schema.
Otherwise forward-fix the application. Restore a database backup only through a
separately approved incident procedure because it loses post-backup writes.

For manual application rollback:

```bash
export WATCHTOWER_IMAGE_TAG="$(cat /opt/watchtower/.deploy/previous)"
docker compose --env-file .env.deploy -f compose.deploy.yaml \
  up -d --no-deps --wait api worker
```

## Backups and dependency operations

- Schedule encrypted PostgreSQL backups outside the database container and test
  restores. A named Docker volume is persistence, not a backup.
- Back up the raw-storage volume consistently with database provenance. Redis is
  transport rather than the job source of truth; its AOF improves staging
  continuity but does not replace PostgreSQL backup.
- Monitor EC2 disk space, container restarts, API readiness, database saturation,
  queue active/oldest values, backup age, and TLS/credential expiry.
- Pin and review immutable image digests before production. Task 16 uses exact
  application SHA tags but upstream image tags still require routine scanning
  and controlled updates.
- Keep database and Redis off host/public ports. If later replaced by managed
  services, require private networking, encryption in transit, authentication,
  least-privilege credentials, backup/restore tests, and bounded timeouts.

## Production blockers

This baseline must remain private until publication-state filtering,
identity-aware operator authentication and authorization, shared edge rate
limits/TLS, approved shared object storage, deny-by-default egress, operational
monitoring/backups, and incident ownership satisfy the Task 15 threat model.
The default Swagger UI also loads browser assets from a third party and should be
restricted or self-hosted under a production content policy.
