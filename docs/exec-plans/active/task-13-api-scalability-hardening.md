# Task 13: API scalability hardening

Status: complete, reverified and approved.
Date: 2026-09-29.

## Prior-task verification

Task 12 was approved by the user and reverified before this task began. Its
focused suite passed 2 tests, focused Ruff and Pyright passed, Alembic remained
at `d9f3a5b7c1e4 (head)` without drift, live readiness returned 200, and OpenAPI
retained the STIX route and media type. The exact transition record is in
`task-12-stix-2-1-export.md`.

## Instruction and context review

Read `Instructions/TASK_13_API_SCALABILITY_HARDENING.md`, the approved V1 scope,
actor read design, search design, current API/session/configuration code and
active execution records. `docs/design/system-workflow-reference.md` remains
absent; no contents are inferred for it.

The current API is stateless, read endpoints are bounded, actor timelines use
cursor pagination, PostgreSQL search has GIN indexes, and connection/statement
timeouts already exist. Pool capacity is hardcoded, responses are not
compressed, no application cache is present, and rate limiting has no approved
client-identity or trusted-proxy boundary yet.

## Measurement and implementation plan

1. Add a reproducible local benchmark fixture and concurrent HTTP load runner
   covering actor lookup, 100-item timeline retrieval and cross-entity search.
   Record latency, throughput, response transfer size, status codes and content
   encoding against the unchanged application.
2. Measure database statement counts and representative `EXPLAIN (ANALYZE,
   BUFFERS)` plans for actor, timeline and search paths.
3. Use those results to select bounded improvements. Likely candidates are
   configurable pool capacity, compression of large responses and slow-request
   observability; no cache will be added without a demonstrated target and an
   exact invalidation strategy.
4. Repeat the same benchmark after changes, preserve API response contracts,
   and validate concurrency, response sizes, tests, static checks, migrations
   and the live API.
5. Record baseline/results, query plans, decisions, rejected changes and scaling
   triggers in `docs/performance/api-baseline.md`, then stop for review.

## Acceptance record

## Baseline and bottlenecks

The reproducible fixture contained 2,000 actors, 2,000 aliases, 2,099
observations, 499 campaigns and bounded associated records. One Uvicorn process
served 100 requests per scenario at concurrency 10 and 25 with logging enabled.
Raw results are under `docs/performance/results/` and the interpretation is in
`docs/performance/api-baseline.md`.

- Actor lookup used one primary-key statement and was not a bottleneck.
- A 100-event timeline used five statements with no page-size query growth. Its
  slowest database plan was 0.644 ms; serialization and a 176,850-byte response
  dominated the endpoint.
- Broad search used one statement, but its observation branch spent 95.800 ms
  recomputing weighted text vectors across 2,099 matches.
- Concurrency 25 raised latency without errors and did not materially increase
  actor/timeline throughput under the original maximum 10-connection pool.

## Implementation result

- Added `scripts/api_load_test.py` with idempotent `seed`, query-count/plan
  `profile`, concurrent `run`, and marker-scoped `cleanup` commands.
- Added a stored generated observation `tsvector` and reversible migration,
  retaining the GIN index and search response/ranking contract. The measured
  broad-search plan fell from 95.800 ms to 13.580 ms.
- Enabled configurable gzip for responses of at least 1,024 bytes. The measured
  timeline transfer fell 92.7% and search transfer fell 89.6%.
- Made pool size, overflow and recycle configurable with bounded defaults of
  10, 10 and 1,800 seconds, plus LIFO connection reuse.
- Added configurable structured slow-request warnings at 500 ms.
- Preserved stateless API instances. No cache or process-local rate limiter was
  added because safe invalidation and trusted caller identity are not defined.
- Documented exact results, limitations, cache/rate decisions and scaling
  triggers in `docs/performance/api-baseline.md` and setup configuration.

## Validation result

- Baseline and after-change runs:
  `.\.venv\Scripts\python.exe scripts/api_load_test.py run --requests 100
  --concurrency 10` and the same command with `--concurrency 25`: PASS, 1,200
  total measured responses returned 200 across both states.
- `.\.venv\Scripts\python.exe scripts/api_load_test.py profile`: PASS before and
  after; actor/timeline/search statement counts remained 1/5/1.
- `.\.venv\Scripts\python.exe scripts/api_load_test.py cleanup`: PASS; zero
  benchmark sources, actors and observations remained.
- `.\.venv\Scripts\alembic.exe downgrade d9f3a5b7c1e4` then
  `.\.venv\Scripts\alembic.exe upgrade head`: PASS with the populated fixture.
- `.\.venv\Scripts\alembic.exe heads`, `current`, and `check`: PASS at
  `a1c3e5f7b9d2 (head)` with no drift.
- `.\.venv\Scripts\pytest.exe -q`: PASS, 76 tests. The existing Starlette
  TestClient/httpx deprecation warning remains.
- `.\.venv\Scripts\ruff.exe check .`: PASS.
- `.\.venv\Scripts\ruff.exe format --check .`: PASS, 107 files formatted.
- `.\.venv\Scripts\pyright.exe`: PASS, zero errors and warnings.
- `git diff --check`: PASS. The repository still has no tracked baseline, so
  files appear as untracked rather than in a conventional diff.
- Live API: readiness and health returned 200; the small health response stayed
  identity encoded and OpenAPI returned gzip. The live database remained empty
  after benchmark cleanup.

## Acceptance review

- PASS: representative actor lookup, timeline, search and concurrency were
  measured with response sizes, statement counts and analyzed query plans.
- PASS: the load/profile fixture is lightweight, reproducible, idempotent and
  explicitly limited to non-production use.
- PASS: measured search and transfer bottlenecks received bounded improvements.
- PASS: indexes, cursor pagination, pool settings, compression, cache candidates,
  request limits, rate limiting and statelessness were evaluated and documented.
- PASS: public response bodies, ranking, pagination and error contracts remain
  unchanged.
- PASS: no Redis response cache, distributed architecture, extra service,
  sharding, Kubernetes or CDN-specific behavior was introduced.

## Concrete remaining risks

- The benchmark is synthetic and local. It does not establish a production SLO,
  replica count or internet-facing capacity.
- A 100-event timeline still reached 1,135 ms p95 at concurrency 25. Its SQL is
  bounded; serialization and nested response construction remain the next
  measured optimization target if production traffic requires pages this large.
- The stored observation search document trades faster reads for additional row
  storage and write-time generation. Task 13 measured the read benefit but not
  high-volume ingestion cost.
- Pool capacity is per process. Deployment must budget total connections across
  API and worker processes against PostgreSQL limits.
- Rate limiting remains deferred until an authenticated or trusted-proxy caller
  boundary is defined. Actor reads therefore remain local-only as already
  required by setup guidance.
- `docs/design/system-workflow-reference.md` remains absent.

## Human review checkpoint

Task 13 is complete and stopped for user approval. Task 14 has not started.

## Transition verification and approval

The user approved moving to the next task on 2026-09-29. Before Task 14 began,
the current performance implementation, migration, measurements, tests and
execution records were inspected. `git diff --check` passed; the repository
still has no tracked baseline, so files remain reported as untracked rather than
as a conventional diff.

The focused foundation/actor/search suite passed 19 tests, focused Ruff and
Pyright passed, Alembic remained at `a1c3e5f7b9d2 (head)` with no drift, and
live readiness returned 200. Small health output remained identity encoded and
large OpenAPI output remained gzip encoded. Task 13 therefore passed its
transition gate with no remaining blocker.
