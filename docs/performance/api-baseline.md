# API scalability baseline

Date: 2026-09-29. Scope: Task 13 local read/API measurement.

## Test shape and reproducibility

The benchmark ran one Uvicorn process on `127.0.0.1:8000` against the local
PostgreSQL 17 container. Application request and access logging remained enabled.
The client and server ran on the same Windows host, so these numbers compare code
paths and are not production capacity claims or network tests.

`scripts/api_load_test.py` creates an idempotent, marked fixture with 2,000
actors, 2,000 aliases, 2,099 observations, 499 campaigns, 25 behaviors, 25
techniques and 10 evidence records. The primary actor has 100 timeline events,
each with evidence, behavior and technique detail. The runner warms each route
five times, then issues 100 requests per scenario at concurrency 10 or 25:

- actor lookup by UUID,
- a 100-event actor timeline,
- cross-entity search for the intentionally broad `benchmark beacon` query with
  a 25-result limit.

Run from the repository root against a non-production database:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe scripts/api_load_test.py seed
.\.venv\Scripts\python.exe scripts/api_load_test.py profile
.\.venv\Scripts\python.exe scripts/api_load_test.py run --requests 100 --concurrency 10
.\.venv\Scripts\python.exe scripts/api_load_test.py run --requests 100 --concurrency 25
.\.venv\Scripts\python.exe scripts/api_load_test.py cleanup
```

The cleanup command deletes only records carrying the fixed Task 13 marker. The
validated run removed the fixture and confirmed zero remaining benchmark sources,
actors and observations in the previously empty development database.

## Before-change baseline

The client requested gzip in both runs. The unchanged server returned identity
responses because compression was not configured.

| Scenario | Concurrency | p50 ms | p95 ms | Requests/s | Transfer bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Actor lookup | 10 | 52.914 | 115.102 | 151.14 | 173 |
| Timeline, 100 events | 10 | 353.181 | 471.408 | 27.97 | 176,850 |
| Search, 25 results | 10 | 253.841 | 340.133 | 36.23 | 10,423 |
| Actor lookup | 25 | 132.071 | 351.739 | 138.61 | 173 |
| Timeline, 100 events | 25 | 882.265 | 1,185.550 | 26.64 | 176,850 |
| Search, 25 results | 25 | 593.661 | 761.420 | 38.33 | 10,423 |

All 600 measured responses returned 200. Raising concurrency from 10 to 25 did
not improve actor or timeline throughput and increased their latency. The pool
could open at most 10 connections (`pool_size=5`, `max_overflow=5`), but database
plans showed that the timeline was primarily API serialization and transfer work,
not slow SQL.

## Query counts and plans

The profile command instruments SQLAlchemy statements and executes `EXPLAIN
(ANALYZE, BUFFERS, FORMAT JSON)` for every representative SELECT.

| Scenario | Statements | Profiled DB time before | Plan finding |
| --- | ---: | ---: | --- |
| Actor lookup | 1 | 3.570 ms | Primary-key index scan; 0.041 ms execution |
| Timeline, 100 events | 5 | 13.972 ms | Bounded eager loads; slowest plan 0.644 ms; no N+1 growth |
| Search, 25 results | 1 | 103.472 ms | Broad observation branch dominated execution at 95.800 ms |

The broad query matched all 2,099 benchmark observations. PostgreSQL reasonably
selected a sequential scan, but the expression-index design recomputed the
weighted observation `tsvector` for every match before ranking. This was the
only measured database bottleneck. Timeline query-count coverage already proves
that the five-query shape stays constant as page size changes.

## Improvements

1. The observation search document is now a PostgreSQL stored generated
   `tsvector` with the existing GIN index name. Search uses the stored value for
   matching and rank calculation. A reversible Alembic migration creates it;
   response ranking and fields are unchanged.
2. Gzip is enabled for responses of at least 1,024 bytes at compression level 5.
   Small actor responses remain identity encoded. The size and level are bounded
   settings.
3. Pool capacity is configurable and defaults to 10 persistent plus 10 overflow
   connections, with a 30-minute recycle and LIFO reuse. Connect, pool-wait and
   statement timeouts remain bounded. Each process has its own pool, so deployment
   must multiply these values by the number of API and worker processes.
4. Requests taking at least 500 ms now produce a structured `slow_request`
   warning with request ID, route, status and duration. The threshold is bounded
   and configurable.

No cache was added. Actor, timeline and search results change when observations,
aliases, evidence, associations or source records change; there is no single
version key that safely invalidates these responses yet. Redis remains limited
to job dispatch. No application rate limiter was added because the current
public reads have neither an authenticated caller identity nor an approved
trusted-proxy boundary. Adding process-local rate state would also violate the
stateless-instance requirement.

## After-change results

| Scenario | Concurrency | p50 ms | p95 ms | Requests/s | Transfer bytes | Encoding |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Actor lookup | 10 | 48.462 | 125.388 | 156.83 | 173 | identity |
| Timeline, 100 events | 10 | 355.629 | 453.634 | 28.06 | 12,957 | gzip |
| Search, 25 results | 10 | 105.910 | 186.605 | 85.36 | 1,082 | gzip |
| Actor lookup | 25 | 126.222 | 414.548 | 134.46 | 173 | identity |
| Timeline, 100 events | 25 | 787.788 | 1,135.295 | 28.44 | 12,957 | gzip |
| Search, 25 results | 25 | 286.524 | 618.331 | 79.99 | 1,082 | gzip |

At concurrency 10, timeline transfer size fell 92.7% with essentially unchanged
throughput, and search transfer size fell 89.6%. Search throughput increased
135.6% and p95 latency fell 45.1%. At concurrency 25, search throughput increased
108.7%; timeline throughput increased 6.8%. Small actor lookup stayed effectively
unchanged and is intentionally not compressed. Variation in its p95 shows why
this local run should be used for comparisons rather than an absolute SLO.

The post-change search plan still chooses a sequential scan for the deliberately
non-selective query, but stored-vector execution fell from 95.800 ms to 13.580 ms
(85.8%). Profiled search database time fell from 103.472 ms to 19.654 ms. Actor
lookup remained one statement and timeline remained five.

Raw results are retained under `docs/performance/results/` for both concurrency
levels and both query profiles.

## Limits and scaling triggers

- Keep the normal timeline page at 25; use 100 only for clients that need it.
  Revisit serialization or a narrower representation if representative p95
  remains above 500 ms at the expected concurrency after network testing.
- Alert on pool timeouts and slow-request rate. Increase pool capacity only while
  PostgreSQL connection headroom exists. Total possible connections equal
  `(pool size + overflow) × API/worker processes`.
- Add Uvicorn processes or stateless API instances when one process saturates a
  CPU core while PostgreSQL has headroom. Keep sessions, caches and rate state
  outside process memory.
- Re-run `EXPLAIN (ANALYZE, BUFFERS)` when table cardinality or search vocabulary
  changes. A selective query using a sequential scan, or a sustained plan above
  100 ms, is a trigger to reassess statistics and indexes.
- Consider a cache only after production measurements show repeated identical
  reads and a version key can cover every contributing record. Candidate actor
  detail is simple; timeline, references and search require broader invalidation.
- Add rate limiting at the authenticated edge or trusted reverse proxy when the
  public deployment boundary is approved. Define caller identity, forwarded-IP
  trust and operator exemptions before choosing limits.
- The test is local and contains synthetic text. Repeat it on production-like
  hardware, network distance and realistic data distributions before setting an
  SLO or deployment replica count.
