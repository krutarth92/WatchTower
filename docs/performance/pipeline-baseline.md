# Pipeline performance baseline

Status: Task 14 measured baseline, 2026-09-29.

## Scope and method

The benchmark exercises the current `mitre_attack_refresh` path with generated,
deterministic STIX 2.1 intrusion-set objects. It uses the production parser,
normalizer, validator, deduplication queries and persistence services against the
local PostgreSQL database. It also measures raw intake through the local object
store, entity resolution against generated actors, and real Dramatiq message
enqueueing through Redis.

All database fixture work runs inside one outer transaction and is rolled back.
The Redis test uses a unique namespace, verifies queue depth, and flushes that
namespace when complete. It does not fetch MITRE ATT&CK from the network. The
external-fetch number uses `httpx.MockTransport`, so it measures connector
overhead rather than internet latency.

The recorded workload is 250 STIX objects in a 110,081-byte bundle, 1,000 actor
rows for resolution, and 1,000 Redis messages. Measurements ran on Python
3.12.14 under Windows 11 with local PostgreSQL and Redis in Docker Desktop. They
are development-machine baselines rather than production capacity guarantees.

Run the same workload from the repository root:

```powershell
uv run --locked python scripts/pipeline_benchmark.py `
  --objects 250 --resolution-actors 1000 --messages 1000 `
  --output docs/performance/results/pipeline-local.json
```

## Results

The `before` and `after` runs use the same workload. Task 14 adds controls and
observability rather than changing persistence behavior, so small differences
are normal run-to-run variation.

| Stage | Before | After | Interpretation |
| --- | ---: | ---: | --- |
| Mock external fetch | 0.711 ms | 1.310 ms | Network latency intentionally excluded |
| Raw intake | 12.803 ms | 13.155 ms | About 8.4 MB/s for this small local object |
| Bundle parse and validation | 1.130 ms | 1.076 ms | More than 220k objects/s; not limiting |
| First full pass | 2,270.016 ms | 2,160.604 ms | 110.13 to 115.71 objects/s |
| Record parse | 10.583 ms | 9.412 ms | Small share of first pass |
| Normalize | 10.386 ms | 9.621 ms | Small share of first pass |
| Validate | 19.339 ms | 18.314 ms | Small on first pass |
| Deduplicate | 481.737 ms | 458.281 ms | Largest read/query cost |
| Persist | 917.747 ms | 875.718 ms | Largest measured stage |
| Replay full pass | 1,853.593 ms | 1,743.136 ms | 134.87 to 143.42 objects/s |
| Exact actor resolution | 19.329 ms | 19.114 ms | Outside the ATT&CK job path |
| No-match actor scan, 1,000 actors | 76.668 ms | 73.759 ms | Linear candidate scan is a future concern |
| Redis/Dramatiq enqueue, 1,000 messages | 702.895 ms | 653.698 ms | 1,423 to 1,530 messages/s |

Raw results are in [`task14-before.json`](results/task14-before.json) and
[`task14-after.json`](results/task14-after.json).

Replay persistence is nearly zero because existing observations are retained.
Replay validation and deduplication each took about 492 ms in the second run;
they reload existing evidence and observations from PostgreSQL. The gap between
the sum of timed record stages and the full pass includes source registration,
normalization-ledger lifecycle work, flushes and connector orchestration.

Embeddings have a storage and retrieval boundary but no configured ingestion
provider. AI is disabled and absent from deterministic ingestion. Neither stage
has a meaningful runtime number. Live external latency was not measured because
it is controlled by the remote source and network; it is bounded separately by
fetch timeouts.

## Bottlenecks and controls

PostgreSQL writes and per-record deduplication queries are the practical limit
for the current job. Redis enqueue throughput is over ten times first-pass object
throughput, so replacing Redis or adding Kafka is not supported by this evidence.
Parsing, normalization and bundle validation do not justify separate scaling.

The worker defaults to one process and two threads. Both values are configurable,
but each process creates its own database pool. Increase concurrency only after
measuring database CPU, I/O, lock waits and connection use under simultaneous
real jobs. The job hard timeout defaults to 240 seconds and must leave at least
five seconds before the 300-second durable lease expires. HTTP total and connect
timeouts default to 30 and 10 seconds.

PostgreSQL remains the queue source of truth. The protected metrics endpoint
reports queued, due, processing, active, capacity, available and oldest queued
time. Submission uses a transaction-scoped advisory lock so the active-job
capacity check and insert cannot race. Duplicate idempotency keys still return
their existing job when capacity is full. New distinct work receives HTTP 429
once active queued-plus-processing jobs reaches the configured default of 1,000.
Recovery and due-job dispatch are bounded to 100 rows per worker boot pass.

Only one job kind exists and it has one resource profile, so a second queue would
add operational cost without isolating a measured workload. Keep the single
`ingestion` queue until at least two job classes need materially different
concurrency, timeout or priority policies.

## Scaling triggers

- Optimize or batch persistence when a representative production workload
  cannot meet its ingestion window and database write time remains dominant.
- Add indexes or a set-based deduplication pass when deduplication latency grows
  materially with retained observation volume, confirmed with `EXPLAIN ANALYZE`.
- Replace the in-memory actor candidate scan when actor count or no-match
  resolution p95 exceeds the product latency budget. Entity resolution is not
  currently called by the ATT&CK refresh job.
- Raise worker processes or threads only while database connection, CPU, I/O and
  lock-wait headroom remain healthy and throughput improves in a concurrency
  benchmark.
- Add a separate worker queue when a second approved job kind has a measured
  resource profile or service objective that conflicts with ATT&CK refresh.
- Revisit Redis capacity only if measured enqueue/dequeue latency or memory use,
  rather than database processing, becomes the limiting stage.
- Move raw storage from the local adapter to S3-compatible shared storage before
  running workers on more than one host.
