# WATCHTOWER development setup

WATCHTOWER currently provides FastAPI, validated configuration, JSON application
logs, SQLAlchemy sessions, Alembic, local PostgreSQL/Redis service definitions,
the intelligence model, actor-centric reads, durable Dramatiq ingestion jobs,
a deterministic PostgreSQL search baseline, a disabled-by-default grounded
research RAG boundary, faithful technical artifact storage, and a reproducible
CI/private-staging deployment baseline. It also provides versioned living
intelligence advisories with an explicit publication boundary. Frontend work
remains a later task.

## Prerequisites and startup

Use Python 3.12, uv, Git, and Docker with Compose and Linux-container support.
Pyright needs Node.js on PATH (its Python wrapper can download Node if absent).
Python 3.12–3.13 are supported; validation used 3.12. Run from the repository root:

```powershell
uv sync --locked
Copy-Item .env.example .env
```

Replace the placeholder password in BOTH POSTGRES_PASSWORD and
WATCHTOWER_DATABASE_URL in .env. URL-encode special characters in the URL password.
Keep the database/user names consistent. Shell variables override .env settings.
The .env file is ignored by Git.

```powershell
docker compose config --quiet
docker compose up -d --wait
uv run --locked alembic upgrade head
uv run --locked uvicorn watchtower.main:create_app --factory --host 127.0.0.1 --port 8000
```

Start the ingestion worker in another terminal after PostgreSQL, Redis and the
latest migration are ready:

```powershell
uv run --locked python -m watchtower.workers.run
```

The worker requeues expired processing leases and dispatches due durable jobs
when it starts. PostgreSQL is the job source of truth; Redis messages contain
only a job UUID. Stopping and restarting the worker is safe: an interrupted job
becomes eligible for recovery after `WATCHTOWER_INGESTION_JOB_LEASE_SECONDS`.

PostgreSQL and Redis bind only to localhost on 5432 and 6379. Adjust the Compose
bindings and database URL together if ports conflict. The PostgreSQL volume
persists across `docker compose down`. Changing .env credentials does not change
users/passwords in an initialized database; do not delete volumes to fix this.

In another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

/health returns 200 with status ok without querying the database. /ready runs
SELECT 1 and returns 200/ready or 503/not_ready without exposing connection errors.
Pool, connection and statement timeouts are bounded. Readiness checks database
connectivity, not schema version or Redis. OpenAPI documentation is at
http://127.0.0.1:8000/docs.

Responses of at least 1 KiB are gzip-compressed when the client advertises gzip.
Database pool size, overflow, recycling and slow-request logging are configurable;
multiply per-process pool capacity by the number of API and worker processes
before deployment. Task 13 measurements and the reproducible local load command
are documented in `docs/performance/api-baseline.md`.

Incoming HTTP bodies default to a 64 KiB limit and oversized declared or
streamed requests return 413. Responses send `X-Content-Type-Options: nosniff`
and `Referrer-Policy: no-referrer`; operator routes also send
`Cache-Control: no-store`. The fixed-source connector refuses redirects and
encoded responses and ignores ambient proxy settings. See
`docs/security/threat-model.md` for the complete threat assessment and the
deployment controls required before public exposure.

The read-only actor API is under `/api/v1/actors`. Swagger documents stable-ID
lookup, bounded name/alias search, aliases, observations, timeline,
behavior/technique associations and source/evidence references. Observation and
timeline lists use opaque cursor pagination; copy `page.next_cursor` into the
next request's `cursor` parameter. Every response returns `X-Request-ID`, and a
safe caller-supplied value is propagated into structured request logs.

Cross-entity search is available at `/api/v1/search`. It covers actors, aliases,
campaigns, behaviors, techniques, observations and sources using PostgreSQL
full-text search plus exact-match boosts. For example:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/search?q=credential+phishing'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/search?q=T1059.001&entity_type=technique'
```

Repeat `entity_type` to select multiple categories. Optional `source_id`,
`intelligence_type`, `date_from`, `date_to` and `limit` filters are documented
in Swagger. Intelligence/date filters intentionally return only observations
and campaigns. Ranking behavior and limitations are documented in
`docs/search/search-baseline.md`.

The operator research contract is at
`POST /api/v1/operations/research/answers`. It is intentionally unavailable in
the default setup: no live embedding or synthesis provider ships with the
project, source text may not leave the machine, and external-model spend is
zero. Its full grounding, citation, actor/time filtering and failure behavior is
exercised with deterministic providers in the Task 10 evaluation. See
`docs/design/evidence-rag-v1.md` before adding a provider. Setting
`WATCHTOWER_RAG_ENABLED=true` alone does not install or configure a provider.

Technical artifact reads are available under
`/api/v1/operations/artifacts` and require the operator token. The collection
endpoint searches and filters STIX 2.1, Sigma and ATT&CK technique metadata; the
ID endpoint returns the exact stored source text, parsed structure, validation
result and provenance. Artifact ingestion is currently an internal service used
by source processing, with no public or operator write endpoint. Validation and
atomicity rules are documented in `docs/design/technical-artifact-handling.md`.

Published living intelligence is available under `/api/v1/advisories`.
Draft creation, immutable revision creation, publication and timestamped update
append operations are under `/api/v1/operations/advisories` and require the
operator token. Drafts and unpublished revisions are never returned by public
routes. Section-level OBSERVED/ASSESSED labels, evidence, actor, campaign and
technique links, publication history, and update pagination are documented in
`docs/design/living-intelligence-advisories.md`.

No authentication or publication-state filter exists for actor reads yet. Keep
Uvicorn bound to `127.0.0.1`; do not expose these routes to the internet until
the later security, publication and deployment tasks establish that boundary.

The ingestion submission and status endpoints are under
`/api/v1/operations/ingestion/jobs` and require the
`X-WATCHTOWER-Operator-Token` header. Configure a random token of at least 32
characters in `.env`, then submit the approved ATT&CK refresh job with a unique
idempotency key:

```powershell
$headers = @{ 'X-WATCHTOWER-Operator-Token' = $env:WATCHTOWER_OPERATOR_TOKEN }
$body = @{
  job_kind = 'mitre_attack_refresh'
  idempotency_key = "manual-$([guid]::NewGuid())"
} | ConvertTo-Json
$job = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/operations/ingestion/jobs `
  -Headers $headers -ContentType application/json -Body $body
$job.data.job
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/operations/ingestion/jobs/$($job.data.job.id)" `
  -Headers $headers
```

PowerShell does not automatically load `.env`; either set the token in the
terminal or replace the header value locally. Reusing the same idempotency key
returns the original job with `duplicate=true`.

Read durable queue depth and admission capacity from the protected metrics route:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/v1/operations/ingestion/jobs/metrics `
  -Headers $headers
```

Queued plus processing jobs are bounded by `WATCHTOWER_INGESTION_MAX_ACTIVE_JOBS`.
A distinct submission above that limit returns HTTP 429; an idempotent replay
still returns its existing job. Worker process/thread settings apply through the
settings-backed launcher above. Each worker process creates its own database
pool, so increase concurrency only after measuring database headroom. Task 14's
method, results and scaling triggers are in
`docs/performance/pipeline-baseline.md`.

## CI and private staging deployment

GitHub Actions in `.github/workflows/ci.yml` install the locked environment and
run Ruff, Pyright, Alembic checks, the PostgreSQL-backed test suite, package and
container builds, dependency auditing, and a HIGH/CRITICAL image scan. There is
no frontend tree, so no frontend job exists yet. Run the equivalent application
checks locally with the commands in Validation below.
The one documented audit exception and its removal criteria are in
`docs/security/dependency-audit-exceptions.md`.

The backend image is built from `Dockerfile` and runs as a non-root user. The
approved non-production target is a single private Ubuntu EC2 host using
`compose.deploy.yaml`. Deployment is manual through the protected `staging`
GitHub Environment; no workflow deploys to production or on push. Copy
`.env.deploy.example` to `.env.deploy` only on the host and replace every
placeholder. The complete host setup, migration order, health checks, backup
expectations, and rollback limits are in
`docs/deployment/ubuntu-ec2-staging.md`.

The staging Compose stack publishes the API only on EC2 loopback and keeps
PostgreSQL and Redis on an internal container network. Its local raw-storage
volume is appropriate only for this single-host baseline. Keep the deployment
private until the production blockers in `docs/security/threat-model.md` and the
deployment runbook are resolved.

## Configuration

| Variable | Default / requirement |
| --- | --- |
| WATCHTOWER_DATABASE_URL | Required; postgresql+psycopg URL with host and database |
| WATCHTOWER_ENVIRONMENT | development; also test, staging or production |
| WATCHTOWER_LOG_LEVEL | INFO |
| WATCHTOWER_DB_CONNECT_TIMEOUT | 3 seconds, range 1–30 |
| WATCHTOWER_DB_POOL_TIMEOUT | 3 seconds, range 1–30 |
| WATCHTOWER_DB_POOL_SIZE | 10 persistent connections per process, range 1–50 |
| WATCHTOWER_DB_MAX_OVERFLOW | 10 temporary connections per process, range 0–100 |
| WATCHTOWER_DB_POOL_RECYCLE_SECONDS | 1800 seconds, range 60–86400 |
| WATCHTOWER_DB_STATEMENT_TIMEOUT_MS | 3000 milliseconds, range 100–30000 |
| WATCHTOWER_RESPONSE_GZIP_MINIMUM_SIZE | 1024 bytes, range 256–1048576 |
| WATCHTOWER_RESPONSE_GZIP_COMPRESSLEVEL | 5, range 1–9 |
| WATCHTOWER_API_SLOW_REQUEST_MS | 500 milliseconds, range 50–60000 |
| WATCHTOWER_MAX_REQUEST_BODY_BYTES | 65536 bytes, range 1 KiB–10 MiB |
| WATCHTOWER_RAW_STORAGE_PATH | storage/raw |
| WATCHTOWER_MAX_RAW_EVIDENCE_BYTES | 10485760 (10 MiB), range 1 KiB–100 MiB |
| WATCHTOWER_REDIS_URL | redis://127.0.0.1:6379/0 |
| WATCHTOWER_OPERATOR_TOKEN | Optional; at least 32 characters; required to enable operator endpoints |
| WATCHTOWER_INGESTION_JOB_MAX_ATTEMPTS | 3, range 1–10 |
| WATCHTOWER_INGESTION_JOB_LEASE_SECONDS | 300 seconds, range 30–3600 |
| WATCHTOWER_INGESTION_JOB_TIMEOUT_SECONDS | 240 seconds, range 10–3595; must leave 5 seconds before lease expiry |
| WATCHTOWER_INGESTION_JOB_RETRY_BASE_SECONDS | 5 seconds, range 1–300 |
| WATCHTOWER_INGESTION_MAX_ACTIVE_JOBS | 1000 queued plus processing jobs, range 1–100000 |
| WATCHTOWER_INGESTION_RECOVERY_BATCH_SIZE | 100 durable jobs per startup recovery/dispatch pass, range 1–1000 |
| WATCHTOWER_INGESTION_WORKER_PROCESSES | 1, range 1–16 |
| WATCHTOWER_INGESTION_WORKER_THREADS | 2 per process, range 1–32 |
| WATCHTOWER_INGESTION_FETCH_TIMEOUT_SECONDS | 30 total seconds, range 5–300 |
| WATCHTOWER_INGESTION_FETCH_CONNECT_TIMEOUT_SECONDS | 10 seconds, range 1–60; cannot exceed total fetch timeout |
| WATCHTOWER_RAG_ENABLED | false; endpoint also requires an explicitly configured provider |
| WATCHTOWER_RAG_CONTEXT_TOKEN_BUDGET | 4000 approximate tokens, range 500–32000 |
| WATCHTOWER_RAG_RETRIEVAL_LIMIT | 12 candidate evidence records, range 1–50 |
| WATCHTOWER_RAG_MAX_COSINE_DISTANCE | 0.45 relevance cutoff, range 0–2 |
| POSTGRES_DB / POSTGRES_USER | watchtower; used by Compose |
| POSTGRES_PASSWORD | Required by Compose |

Application lifecycle/readiness logs are JSON. Driver exception messages are
omitted from application logs; only exception classes are recorded. Uvicorn keeps
its standard server/access log format. Operator authentication protects ingestion
job writes and status reads; actor reads remain unauthenticated and locally bound.

## Validation

```powershell
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyright
uv run --locked alembic heads
uv run --locked alembic upgrade head --sql
```

The PostgreSQL integration check is skipped unless a test database URL is supplied.
A test run with this skip is not full foundation validation. With the development
PostgreSQL running, use its URL for this read-only check:

```powershell
$env:WATCHTOWER_TEST_DATABASE_URL = 'postgresql+psycopg://watchtower:YOUR_PASSWORD@127.0.0.1:5432/watchtower'
uv run --locked pytest -m integration
Remove-Item Env:WATCHTOWER_TEST_DATABASE_URL
```

Verify /ready returns 503 after `docker compose stop postgres`, /health stays 200,
and /ready recovers after `docker compose up -d --wait postgres`. Use only the
local development service. Run `uv run --locked alembic current` and
`uv run --locked alembic check` against the running database. Task 02 adds the
first domain migration; always run `alembic upgrade head` after syncing changes.
Sessions roll back uncommitted work on close; write services must commit explicitly.

Task 03's connector-facing intake stores immutable raw objects below
`WATCHTOWER_RAW_STORAGE_PATH`; `/storage/` is ignored by Git. Object keys are
content-addressed and source-scoped. The local adapter is for development and
tests; deployment must configure an S3-compatible implementation before relying
on multiple API/worker hosts. Intake defaults to a 10 MiB per-object limit.

## Dependency maintenance

pyproject.toml is the direct-dependency source; uv.lock records resolution.
Requirements files are generated, hash-pinned compatibility exports:

```powershell
uv lock
uv export --frozen --no-dev --no-emit-project --output-file requirements.txt
uv export --frozen --no-emit-project --output-file requirements-dev.txt
```

For pip workflows, install an export first, then `pip install --no-deps -e .`.
The export excludes the local project. Use `uv sync --locked` as the standard.

## Local environment and project context

In the initial Codex shell Python, uv and Docker were absent from PATH. Bundled
Python 3.12 was used; uv was installed into ignored .tools/ with .uv-cache/ as its
cache. Other developers should use their normal uv installation on PATH. Docker
Desktop is installed per-user at
`C:/Users/Admin/AppData/Local/Programs/DockerDesktop`; its CLI directory is not
on this shell's PATH. Compose and live PostgreSQL validation passed using its
`resources/bin/docker.exe`. See the active execution plans for exact results.

The original task bundle and guides remain ignored locally. AGENTS.md records
the prior-task verification rule. The original system workflow reference remains
unavailable; the user approved the V1 proposal as the Task 01 baseline.
