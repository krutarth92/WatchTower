# Task 16: CI/CD and deployment baseline

Status: complete, reverified and approved; Task 17 started.
Date: 2026-09-29.

## Prior-task verification

Task 15 was approved and reverified before this task began. Its focused security
suite, static checks, migration state and live security behavior passed. The
exact result is recorded in the Task 15 execution plan.

## Target and plan

Use one private, non-production Ubuntu EC2 host running the WATCHTOWER API and
worker as containers with Docker Compose. The baseline will connect to
PostgreSQL and Redis described by environment URLs and use a persistent local
raw-storage volume only for single-host staging. Production exposure remains
blocked by the publication, identity, edge-rate-limit, shared object-storage and
operations gates in the threat model.

1. Add a reproducible non-root backend image and container ignore rules.
2. Add GitHub Actions for locked installation, PostgreSQL-backed tests, Ruff,
   Pyright, migration checks, package/image builds and practical dependency and
   image scanning. There is no frontend tree, so frontend checks are not added.
3. Add an explicit manual non-production deployment workflow without embedded
   secrets or automatic production execution.
4. Add a staging Compose definition and deployment runbook covering variables,
   migration/deployment order, readiness, rollback, PostgreSQL/Redis/storage,
   backups and known release blockers.
5. Validate workflows/configuration, build and smoke-test the image locally,
   run the complete application suite, then stop for review.

`docs/design/system-workflow-reference.md` remains absent and is not inferred.

## Acceptance record

### Delivered

- Added a locked Python 3.12 backend image that runs as UID 10001, includes an
  API readiness health check, omits development dependencies and installer
  caches, and supports API, worker and one-shot migration roles.
- Added CI for locked installation, Ruff, formatting, Pyright, PostgreSQL-backed
  tests, Alembic state, Python distributions, the backend image, dependency
  audit and HIGH/CRITICAL image scanning. All external actions are pinned to
  full commit SHAs. Dependabot covers Python, actions and Docker inputs.
- Added a manual-only staging deployment workflow using a protected GitHub
  Environment, pinned SSH host identity and exact Git commit SHA. It contains no
  deployment secrets and has no production or push deployment path.
- Added a private single-host Ubuntu EC2 Compose baseline with internal
  PostgreSQL/Redis, loopback-only API publication, a worker egress network,
  one-shot migrations and persistent staging volumes.
- Added the complete environment template, server deployment script, staging
  runbook, rollback limits, backup/dependency guidance and production blockers.
  There is no frontend tree, so frontend CI is not applicable.

### Validation on the final file state

| Command or check | Result |
| --- | --- |
| `.venv\\Scripts\\ruff.exe check .` | PASS |
| `.venv\\Scripts\\ruff.exe format --check .` | PASS, 117 files formatted |
| `.venv\\Scripts\\pyright.exe` | PASS, 0 errors/warnings |
| `.venv\\Scripts\\pytest.exe` with both database URLs loaded from the local `.env` | PASS, 83 tests including 2 PostgreSQL integration tests; one existing Starlette deprecation warning |
| `.venv\\Scripts\\uv.exe lock --check` with workspace cache | PASS, 59 packages resolved and lock unchanged |
| `.venv\\Scripts\\uv.exe build` with workspace cache | PASS, sdist and wheel built |
| `alembic upgrade head`, `heads`, `current`, and `check` against local PostgreSQL | PASS, single/current head `a1c3e5f7b9d2`, no new operations |
| PyYAML `BaseLoader` parse of both workflows, Dependabot and deployment Compose | PASS |
| Git Bash `bash -n scripts/deploy_staging.sh` | PASS |
| `docker compose --env-file .env.deploy.example -f compose.deploy.yaml config --quiet` using the validation overrides | PASS |
| `docker build --tag watchtower:task16 .` | PASS |
| Image import/identity smoke command | PASS, `watchtower create_app 10001` |
| Isolated `watchtower-task16-validation` Compose deployment on `127.0.0.1:8016` | PASS: PostgreSQL/Redis healthy, migration succeeded, API healthy, worker running |
| Live `/health`, `/ready`, `/docs`, and protected metrics checks | PASS: 200/200/200; protected route 401 with `nosniff` and `no-store` |
| Container `alembic current` and `alembic check` | PASS, head current and no drift |
| Worker raw-volume write/delete smoke test | PASS as UID 10001 |
| `pip-audit` over the fully pinned runtime export with pip disabled | PASS with only the two aliases of the documented DiskCache exception ignored |
| Trivy 0.74.0 archive scan matching CI severity settings | PASS, zero fixed HIGH/CRITICAL OS or library findings |
| Validation stack/archive/cache cleanup | PASS; only Task 16 resources were removed |

The first smoke deployment exposed two issues that were fixed and revalidated:
the worker inherited the API-only health check, and an API attached only to an
internal Docker network could not publish its host loopback port. The final
Compose file disables irrelevant health checks and gives the API a separate
ingress bridge while leaving PostgreSQL and Redis internal.

The initial dependency-audit command also attempted platform-specific wheel
installation from the multi-platform hash export. CI now audits exact pins with
dependency resolution and pip installation disabled. The remaining DiskCache
advisory has no patched release and is unreachable in the current code because
WATCHTOWER never creates or reads a DiskCache cache; its bounded exception and
review deadline are recorded in
`docs/security/dependency-audit-exceptions.md`.

### Remaining issues and review checkpoint

- The hosted GitHub Actions run cannot exist until these currently uncommitted
  files are committed and pushed. The equivalent local application, package,
  container, migration, dependency and image checks are green; a hosted run is
  not claimed as executed.
- Upstream container tags remain mutable in this staging baseline. Production
  requires reviewed digests and the release controls in the runbook.
- The DiskCache exception must be reviewed by 2026-12-31 or earlier when its
  dependency path or upstream release changes.
- The production security, shared object-storage, monitoring, backup and
  identity/publication gates in the Task 15 threat model remain blockers.
- `docs/design/system-workflow-reference.md` remains absent and was not invented.

At the original checkpoint Task 17 had not started, and work stopped for human
review as required.

## Transition verification before Task 17

On 2026-10-01 the user explicitly approved the transition by asking to verify
the last task and continue with the next one. The actual Task 16 files and task
instructions were reread. The required system workflow reference remains absent.

- Ruff and the formatter passed on 117 files; Pyright reported no issues.
- Workflow, Dependabot and deployment Compose YAML parsed successfully, and the
  deployment Bash script passed `bash -n`.
- Docker Desktop 29.8.0 was started; local PostgreSQL and Redis reached healthy.
- The complete database-backed suite passed: 83 tests, including both PostgreSQL
  integration tests, with the existing Starlette deprecation warning only.
- The lockfile check passed, the wheel and source archive rebuilt, Alembic was at
  the single/current head `a1c3e5f7b9d2` with no drift, and the current backend
  image rebuilt and imported as UID 10001.
- The previous dependency and image scans remain applicable because no relevant
  dependency, lockfile or image-source file changed after their successful run.
  Hosted GitHub Actions still require a future commit and push and are not
  represented as having run.

Task 16 therefore passed transition verification before Task 17 began.
