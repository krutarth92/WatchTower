# Task 14: pipeline scalability hardening

Status: complete; stopped for human review.
Date: 2026-09-29.

## Prior-task verification

Task 13 was approved by the user and reverified before this task began. Its
focused foundation/actor/search suite passed 19 tests, Ruff and Pyright passed,
Alembic remained at `a1c3e5f7b9d2 (head)` without drift, live readiness returned
200, and live compression thresholds remained correct. The exact transition
record is in `task-13-api-scalability-hardening.md`.

## Instruction and context review

Read `Instructions/TASK_14_PIPELINE_SCALABILITY_HARDENING.md`, the approved V1
scope, raw-intake, normalization, actor-resolution and asynchronous-job designs,
plus the current connector, pipeline, worker and tests.
`docs/design/system-workflow-reference.md` remains absent; no contents are
inferred for it.

The approved ATT&CK job uses one durable PostgreSQL state machine and one
Dramatiq Redis queue. It has bounded payloads, attempts, leases, retry delays,
HTTP timeouts and identifier-only messages. Worker concurrency is currently a
literal setup command, durable queue depth has no operator metric, and new jobs
have no backlog admission threshold. Entity resolution exists but is not called
by the ATT&CK normalization job. Embeddings and AI providers are disabled and
external enrichment is limited to the fixed-source HTTP fetch.

## Measurement and implementation plan

1. Add an optional low-overhead stage recorder to the deterministic
   normalization pipeline without changing its transaction or output contract.
2. Add a reproducible generated benchmark that rolls back all database writes
   and independently measures local intake, bundle parsing, record parsing,
   normalization, validation, deduplication, persistence, replay deduplication,
   exact/worst-case entity resolution and Redis/Dramatiq enqueue throughput.
3. Record whole-pipeline throughput and explicitly mark embeddings, AI and live
   network enrichment as inactive or environment-dependent.
4. Use measurements to set bounded worker concurrency, fetch timeout and durable
   backlog settings. Add operator-visible durable queue depth and race-safe
   backpressure only if the benchmark/current state justify them.
5. Keep one queue unless measurements show independently scalable job classes;
   document why any separate queue or distributed component was rejected.
6. Repeat the benchmark and validate job replay, retries, migration state,
   static checks and live API. Record results and scaling triggers in
   `docs/performance/pipeline-baseline.md`, then stop for review.

## Acceptance record

### Measurement

The generated workload contains 250 deterministic STIX intrusion-set objects
(110,081 bytes), 1,000 actor candidates and 1,000 Redis messages. Database work
runs in an outer transaction and is rolled back; the Redis benchmark uses and
flushes a unique namespace.

The first run measured 110.13 first-pass objects/second and 134.87 replay
objects/second. Persistence took 917.747 ms and deduplication took 481.737 ms,
the two largest record stages. Redis accepted 1,422.69 messages/second. The
repeat run measured 115.71 first-pass objects/second, 143.42 replay
objects/second and 1,529.76 Redis messages/second. Detailed stage results and
limitations are in `docs/performance/pipeline-baseline.md`; raw JSON is retained
under `docs/performance/results/`.

### Implemented controls

- Worker process and thread counts are validated settings used by a settings-backed
  Dramatiq launcher; defaults remain one process and two threads.
- Job and fixed-source HTTP timeouts are bounded and their required relationships
  are validated at startup.
- Active durable jobs are capped. A transaction-scoped advisory lock makes the
  duplicate lookup, capacity check and insert race-safe. Distinct excess work
  receives HTTP 429 while idempotent duplicates retain their existing result.
- The protected metrics route reports durable queued, due, processing, active,
  capacity, available and oldest-queued values.
- Startup recovery/dispatch query sizes are configurable and bounded.
- One queue was retained: only one job kind exists and measured Redis enqueue
  throughput substantially exceeds the database-limited pipeline throughput.

### Validation

- `pipeline_benchmark.py --objects 250 --resolution-actors 1000 --messages
  1000` completed twice and cleaned up its transactional/Redis fixtures.
- Focused integration validation: 20 passed with the existing Starlette
  TestClient deprecation warning.
- Full PostgreSQL-backed suite: 79 passed with the same warning.
- Ruff: all checks passed; 111 files formatted.
- Pyright: 0 errors, 0 warnings, 0 information messages.
- Alembic: `a1c3e5f7b9d2 (head)` is current and `alembic check` reported no new
  upgrade operations.
- Live temporary Uvicorn validation returned health `ok`, readiness 200 and
  queue metrics 200 with all documented fields and capacity 1000. OpenAPI
  includes the metrics route and submission's 429 response.

### Criteria

- Stage-by-stage reproducible workload and throughput/latency results: pass.
- Intake, parsing, normalization, deduplication, resolution, persistence,
  external boundary, embedding and AI status covered: pass.
- Configurable worker concurrency, bounded jobs, timeouts and backpressure: pass.
- Durable queue depth metrics: pass.
- Separate queues and distributed infrastructure added only with evidence: pass;
  measurement rejects both for the current workload.
- Bottleneck analysis, baseline document and future scaling triggers: pass.
- Practical current-architecture bottlenecks understood and documented: pass.

No migration, dependency, unrelated feature or external service integration was
introduced. The task stops here pending human approval.

## Transition verification before Task 15

The user approved Task 14 on 2026-09-29. The actual benchmark report and both
JSON result files were re-read and parsed successfully. The database-backed
foundation/job suite passed 20 tests; focused Ruff formatting/lint and Pyright
passed; Alembic remained at `a1c3e5f7b9d2 (head)` with no new operations; and
the running API returned readiness 200 with the queue-metrics and submission-429
contracts present in OpenAPI. The existing Starlette TestClient deprecation
warning remains non-blocking. Task 14 therefore passed transition verification
before Task 15 began.
