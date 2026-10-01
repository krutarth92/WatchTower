# Task 08: asynchronous ingestion jobs

Status: complete, reverified and approved; Task 09 started.
Date: 2026-09-28.

## Prior-task verification

Task 07 was inspected and fully revalidated before this task began. The exact
commands, results and the user's approval are recorded in
`task-07-actor-timeline-read-api.md`. No required check remains blocked.

## Contract

`docs/design/async-ingestion-jobs.md` defines the durable job, operator API,
idempotency, state machine, retry, lease, recovery, transaction and logging
semantics before implementation. The required
`docs/design/system-workflow-reference.md` remains missing; no contents are
inferred.

## Implementation plan

1. Add Dramatiq with its Redis broker and validated worker/operator settings.
2. Add the ingestion job model and reversible additive migration.
3. Implement idempotent submission, row-locked claiming, bounded retry,
   terminal outcomes and expired-lease recovery.
4. Connect the existing ATT&CK connector to a Dramatiq actor whose payload is
   only a job UUID, with structured job/source/correlation logs.
5. Add token-protected `202` submission and job-status endpoints.
6. Test success, retryable/permanent failure, duplicate submission, recovery,
   transitions, payload size and authentication, then run full validation.

No arbitrary URL/body submission, public unauthenticated write, Kafka,
microservice, LLM, RAG, frontend or unrelated task is in scope.

## Implementation result

- Added a PostgreSQL-backed ingestion job state machine with idempotent
  submission, row-locked claims, attempt bounds, exponential retry, lease
  ownership, terminal outcomes and expired-lease recovery.
- Added a Redis-backed Dramatiq queue and worker for the approved
  `mitre_attack_refresh` connector. Messages contain only the job UUID. The
  worker time limit expires before its lease, and stale completions roll back
  connector writes.
- Added operator-token-protected submission and status routes. Submission
  commits before enqueue and returns `202`; a duplicate key returns the original
  job. A queue outage cannot erase the durable queued record.
- Added the additive/reversible `f2c4d6e8a1b3` migration, settings, generated
  dependency exports, operational instructions and structured safe logging.
- Added integration coverage for success, delayed retry, permanent failure,
  retry exhaustion, duplicate submission/delivery, state transitions, expired
  lease recovery, stale-write rollback, safe error handling, API authentication
  and identifier-only Dramatiq payloads.

## Validation and acceptance

Validation used the configured local PostgreSQL and Redis services on
2026-09-28. Results for the final file state:

- `WATCHTOWER_TEST_DATABASE_URL=<local .env URL> .venv/Scripts/python.exe -m pytest -q`
  — PASS, 59 tests; one Starlette deprecation warning.
- `.venv/Scripts/ruff.exe check .` — PASS.
- `.venv/Scripts/ruff.exe format --check .` — PASS, 74 files formatted.
- `.venv/Scripts/pyright.exe` — PASS, zero errors/warnings.
- `.venv/Scripts/python.exe -m alembic downgrade e4b8c1d2a6f0` followed by
  `... -m alembic upgrade head` — PASS; reversible migration exercised.
- `.venv/Scripts/python.exe -m alembic current`, `heads` and `check` — PASS;
  current and sole head `f2c4d6e8a1b3`, no model drift.
- `UV_CACHE_DIR=.uv-cache .venv/Scripts/python.exe -m uv lock --check` — PASS,
  43 packages resolved. Requirements exports contain Dramatiq 2.2.1 and Redis
  8.1.0.
- Docker Compose `ps` — PASS; PostgreSQL 17 and Redis 7 healthy on localhost.
- A real RedisBroker enqueue/flush smoke — PASS. A real one-process/one-thread
  Dramatiq boot — PASS; recovery completed and the worker became ready.

Acceptance criteria:

- PASS: ingestion runs outside the request in Dramatiq backed by Redis.
- PASS: submit, queued, processing, succeeded and failed behavior is durable and
  observable through the operator API.
- PASS: correlation ID, failure reason, bounded retry and idempotency key are
  persisted.
- PASS: duplicate submission and duplicate delivery cannot create a second job
  or execute a terminal job again.
- PASS: expired leases replay after worker restart, and an old worker cannot
  commit stale connector writes.
- PASS: logs carry job/source/correlation identifiers without raw exception or
  token values; queue messages contain only a UUID.
- PASS: submission returns `202 Accepted` with the job ID and the approved
  private status endpoint reports the current state.
- PASS: no Kafka, microservice split or AI execution was added.

## Remaining issues and checkpoint

The required `docs/design/system-workflow-reference.md` is still unavailable;
its contents were not inferred. Recovery of a durable job whose Redis enqueue
failed occurs when a worker starts, so operators must restart a worker after a
queue outage if the failed enqueue left no message. The existing local raw
object store is not suitable for multiple hosts; the approved V1 scope already
defers selecting an S3-compatible deployment target.

Task 08 is complete. Stop here and obtain explicit human approval before Task
09, as required by `Instructions/TASK_08_ASYNC_INGESTION_JOBS.md` and the root
`AGENTS.md` transition rule.

## Task 09 transition verification

The user's 2026-09-28 request to start the next task satisfies Task 08's human
review checkpoint. Before Task 09 implementation, the actual job model,
migration, services, worker, API, tests, dependency declarations and operations
documentation were inspected again. The required workflow reference remains
missing and no contents were inferred.

Current-state verification passed:

- `WATCHTOWER_TEST_DATABASE_URL=<local .env URL> .venv/Scripts/python.exe -m pytest tests/test_ingestion_jobs.py -q`
  — 10 passed; one Starlette deprecation warning.
- Focused Ruff check and format check across application code, the Task 08 test
  and migration — passed; 41 files formatted.
- Focused Pyright across the same paths — zero errors/warnings.
- `alembic current` and `alembic check` — current at `f2c4d6e8a1b3` with no
  model drift.
- Live `/health` and `/ready` — HTTP 200; both Task 08 OpenAPI paths present.
- Docker Compose PostgreSQL and Redis services — healthy on localhost.

All Task 08 deliverables and acceptance criteria still pass. The documented
recovery and local-object-storage limitations remain visible and do not block
the bounded deterministic-search task. Task 09 may proceed.
