# Task 01: backend foundation

Status: complete, verified and approved for transition to Task 02.
Date: 2026-09-27.

## Prior-task verification

Task 00 was reread and verified against its four planning acceptance criteria.
Results and the user's approval to start Task 01 are recorded in bootstrap.md.
The original system workflow reference remains missing; the approved scope and
current AGENTS.md are the available baseline. No contents were invented.

## Changes

- pyproject.toml: uv package metadata, canonical dependencies, build configuration
  and pytest/Ruff/Pyright settings. uv.lock: resolved dependencies.
- requirements.txt and requirements-dev.txt: generated hash-pinned exports.
- apps/api/src/watchtower/__init__.py and api/core/db package initializers.
- main.py: application factory, lifespan, engine/session factory and cleanup.
- api/health.py: typed health/readiness routes; 503 on database failures.
- core/config.py: environment settings, secret URL and bounded timeout validation.
- core/logging.py: JSON application events without driver exception messages.
- db/base.py and db/session.py: SQLAlchemy metadata, bounded engine and session
  dependency. No domain schema, automatic table creation or implicit commits.
- alembic.ini, alembic/env.py, alembic/script.py.mako and versions/.gitkeep:
  migration framework with no domain revisions.
- compose.yaml and .env.example: PostgreSQL/Redis local services and settings.
- tests/test_foundation.py and tests/test_postgres.py: configuration, lifecycle,
  liveness, readiness failure/recovery, log safety and opt-in real DB checks.
- .gitignore: ignore local tool/cache and clean validation environment directories.
- SETUP.md: install/start/check commands, settings and remaining validation.
- v1-scope.md and bootstrap.md: record approval and verification state.

## Validation performed

Commands were run from the repository root. `uv` below was invoked as
`./.tools/bin/uv.exe`, with UV_CACHE_DIR set to `.uv-cache`.
Python was `C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
Node for Pyright was supplied on PATH from the same runtime's `dependencies/node/bin`.

| Command / check | Result |
| --- | --- |
| uv sync --python <Python path above> | PASS: new .venv; 40 packages installed |
| UV_PROJECT_ENVIRONMENT=.venv-clean; uv sync --locked --python <Python path above> | PASS: independent clean environment, same lock |
| uv export --frozen --no-dev --no-emit-project --output-file requirements.txt | PASS |
| uv export --frozen --no-emit-project --output-file requirements-dev.txt | PASS |
| uv build | PASS: source distribution and wheel |
| .venv/Scripts/python.exe -m pytest | 7 passed, 1 integration test skipped |
| .venv/Scripts/ruff.exe check . | PASS |
| .venv/Scripts/ruff.exe format --check . | PASS: 17 files formatted |
| .venv/Scripts/pyright.exe | PASS: zero errors or warnings |
| .venv/Scripts/alembic.exe heads | PASS: no revisions, as intended |
| .venv/Scripts/alembic.exe upgrade head --sql | PASS: offline BEGIN/COMMIT |
| Actual uvicorn watchtower.main:create_app --factory --host 127.0.0.1 --port 18765 | PASS: temporary process started and stopped; HTTP /health=200, /ready=503 with unreachable DB |
| Source tar inspection using Python tarfile | PASS: 30 entries, no environment/tool/cache directories |
| Compose parsing using yaml.safe_load | PASS: postgres and redis only; not Docker validation |

Alembic offline and Uvicorn smoke checks used a dummy unreachable local database
URL, not real credentials. The startup smoke script used subprocess.Popen,
polled /health with httpx, checked /ready, and terminated its own child in finally.
Sandbox networking blocked dependency downloads and the first localhost probe;
approved escalated retries succeeded. No automatic approval rejection occurred.

Pyright has two narrow reportCallIssue suppressions for Settings() calls because
Pydantic Settings populates the required database URL from the environment.
The tests have one equivalent suppression for their environment-loading check.
No broad diagnostic suppression is enabled.

The test run emits an upstream Starlette warning that its httpx TestClient
integration is deprecated in favor of httpx2. Current locked tests pass; revisit
the test client dependency during an intentional dependency upgrade.

## Acceptance and remaining checks

- PASS: clean dependency installation and package build.
- PASS: API starts and health succeeds over real HTTP.
- PASS: readiness succeeds against PostgreSQL, returns 503 while PostgreSQL is
  stopped, and recovers to 200 after PostgreSQL restarts without restarting API.
- PASS: all 8 automated tests, including the live PostgreSQL check.
- PASS: Ruff lint/format and Pyright checks.
- PASS: Docker Desktop 4.92.0, Engine 29.8.0 and Compose 5.5.1 verified;
  PostgreSQL 17 and Redis 7 containers are healthy with localhost-only ports.
- PASS: online Alembic upgrade/current/check; no ungenerated model operations.

Final Docker/PostgreSQL verification used the per-user Docker executable at
`C:/Users/Admin/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe`.
`docker compose config --quiet` and `docker compose up -d --wait` passed. Images
were pulled once and the named PostgreSQL development volume was created. The
full pytest run reported 8 passed in 1.23 seconds. A pytest cache write warning
was environmental and did not affect test execution or results.

The live transition check started Uvicorn on localhost:18766, confirmed health
and readiness at 200, stopped only the Compose PostgreSQL service, confirmed
health 200 and readiness 503, restarted/waited for PostgreSQL health, confirmed
readiness returned to 200, and stopped the temporary API process.

## Scope and review

No actors, intelligence schema, ingestion, workers, RAG, frontend, STIX or auth
system was implemented. No production deployment or Git commit was performed.
The user's 2026-09-27 instruction to start the next task supplied the Task 01
human review approval, conditional on required verification. Verification now
passes, so Task 02 may begin. PostgreSQL and Redis remain running for Task 02.
