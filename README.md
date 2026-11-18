# WATCHTOWER

WATCHTOWER is an adversary-first cyber threat intelligence product for studying
threat actors, their behavior over time, and the evidence behind each claim.

It provides a FastAPI service, PostgreSQL intelligence model, deterministic
MITRE ATT&CK ingestion, actor timelines, search, evidence-grounded research
contracts, STIX 2.1 export, technical artifact storage, asynchronous jobs, and
versioned living intelligence advisories.

## Current status

The backend is complete for local development and private evaluation. The V1
web interface includes public intelligence, actor research and a local/private
operator integration register built on centralized design tokens. The
[V1 readiness audit](docs/exec-plans/active/v1-readiness.md) records the exact
boundary and remaining UI work.

Production templates define private S3 evidence storage, encrypted Multi-AZ RDS
PostgreSQL, governed backups, Cognito operator identity, and an ALB/WAF HTTPS
edge. They are preserved for the separately gated
[V2 productionization phase](docs/product-specs/v2-productionization-scope.md)
and remain validation-only until an AWS deployment is authorized.

## Quick start

Requirements:

- Docker Desktop or Docker Engine with Compose for the complete local stack
- Python 3.12 or 3.13, [uv](https://docs.astral.sh/uv/), Node.js 24 and
  pnpm 12.14.0 only for host development

From the repository root:

```powershell
Copy-Item .env.example .env
```

Replace the password in `POSTGRES_PASSWORD`, `WATCHTOWER_DATABASE_URL` and
`WATCHTOWER_CONTAINER_DATABASE_URL` with the same local password. Replace the
operator-token placeholder with at least 32 random characters. Then run the
complete application:

```powershell
docker compose config --quiet
docker compose build
docker compose up -d --wait
docker compose run --rm --no-deps api watchtower-demo-data seed
```

Open:

- Web application: <http://127.0.0.1:3000>
- Search: <http://127.0.0.1:3000/search>
- Demo actor: search for `Frost Lantern`
- Demo indicator: search for `telemetry-cdn.example`
- Demo CVE: search for `CVE-2026-45123`
- Integration administration: <http://127.0.0.1:3000/admin/integrations>
- API documentation: <http://127.0.0.1:8000/docs>

The fictional `watchtower_demo/v1` graph is deterministic and explicitly
marked. Repeating `seed` is a no-op. Inspect or remove only that graph with:

```powershell
docker compose run --rm --no-deps api watchtower-demo-data status
docker compose run --rm --no-deps api watchtower-demo-data cleanup
```

Stop the stack without deleting PostgreSQL data:

```powershell
docker compose down
```

For API/web development on the host while PostgreSQL and Redis remain in
Docker, follow the separate workflow in [SETUP.md](SETUP.md).

## Main API areas

- `/api/v1/actors` — actor lookup, evidence and timelines
- `/api/v1/search` — deterministic cross-entity search
- `/api/v1/advisories` — published living intelligence advisories
- `/api/v1/operations/ingestion/jobs` — operator ingestion jobs
- `/api/v1/operations/integrations` — approved source and enrichment roadmap
- `/api/v1/operations/artifacts` — faithful technical artifact reads
- `/api/v1/operations/exports/stix` — actor-centered STIX 2.1 export
- `/api/v1/operations/research/answers` — disabled-by-default grounded research

Operator routes use the `X-WATCHTOWER-Operator-Token` header for local/private
staging. Production requires Cognito-compatible bearer tokens and explicit
`operator`/`publisher` roles.

## Validation

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyright
uv run --locked pytest
uv run --locked alembic check
```

PostgreSQL-backed tests require `WATCHTOWER_TEST_DATABASE_URL`. GitHub Actions
runs the full suite with PostgreSQL and Redis, builds the package and container,
audits dependencies, and scans the container for high-severity vulnerabilities.

## Documentation

- [V1 scope](docs/product-specs/v1-scope.md)
- [V2 productionization scope](docs/product-specs/v2-productionization-scope.md)
- [Integration status](docs/data-sources/integration-status.md)
- [Intelligence data model](docs/design/intelligence-data-model.md)
- [Security threat model](docs/security/threat-model.md)
- [Production security boundary](docs/security/production-boundary.md)
- [Production edge deployment](docs/operations/production-edge-deployment.md)
- [Durable data recovery](docs/operations/durable-data-recovery.md)
- [Private staging deployment](docs/deployment/ubuntu-ec2-staging.md)
- [Living intelligence contract](docs/design/living-intelligence-advisories.md)

## License

See [LICENSE](LICENSE).
