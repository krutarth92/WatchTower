# Asynchronous ingestion jobs

Status: Task 08 implementation contract with Task 14 scaling controls, 2026-09-29.

## Boundary

An operator submission creates a durable PostgreSQL job before a small Dramatiq
message is placed on Redis. The queue message contains only the job UUID. Job
kind, Source, idempotency key, correlation ID, attempts, failure state and result
references remain in PostgreSQL.

Task 08 supports one approved job kind: `mitre_attack_refresh`. Its worker uses
the existing fixed-source ATT&CK connector, immutable raw intake and deterministic
normalization pipeline. No arbitrary URL, uploaded body, AI call or general
document payload is accepted.

## Operator API

`POST /api/v1/operations/ingestion/jobs` accepts job kind and a caller-selected
idempotency key and returns `202 Accepted` with the durable job ID. `GET
/api/v1/operations/ingestion/jobs/{job_id}` returns current state. Both require
the `X-WATCHTOWER-Operator-Token` API-key header and are unavailable when
`WATCHTOWER_OPERATOR_TOKEN` is not configured. Comparison is constant-time and
the token is never logged or returned.

`GET /api/v1/operations/ingestion/jobs/metrics` uses the same operator
authentication and reports durable queued, due, processing and active counts,
the configured capacity and remaining capacity, and the oldest queued time.

The request ID becomes the job correlation ID. A duplicate `(job_kind,
idempotency_key)` returns the original job and `duplicate=true`; it never creates
a second job. Submission commits the job before enqueueing. If Redis is
temporarily unavailable, the durable queued row remains recoverable and the API
still returns the accepted job.

Submission is bounded by the configured active-job capacity. A PostgreSQL
transaction-scoped advisory lock serializes the duplicate lookup, active count
and insert so concurrent submissions cannot overrun the limit. Idempotent
duplicates return their existing job even when capacity is full; distinct work
returns HTTP 429. Active means queued plus processing. Terminal jobs do not use
capacity.

## State and retry contract

State transitions are:

```text
queued -> processing -> succeeded
                    \-> queued (retryable and attempts remain)
                    \-> failed (permanent or attempts exhausted)
processing with expired lease -> queued (worker restart recovery)
```

Workers claim rows under `SELECT ... FOR UPDATE`; the claim increments attempts
and installs a bounded lease. Duplicate Redis delivery is harmless because only
one claimant can move a queued job to processing. Default maximum attempts are
three. Retry delays use bounded exponential backoff and are scheduled only after
the retry state commits. Failure reasons are whitespace-normalized, control-free
and capped at 2,000 characters.

On worker-process boot, recovery returns a bounded batch of expired processing
leases to queued and dispatches a bounded batch of due queued jobs. Repeated
recovery may enqueue duplicate UUID
messages, but database claiming prevents duplicate work. Terminal jobs ignore
replayed messages.

Recovery and dispatch use a configurable batch bound. Worker processes and
threads are configured through `watchtower.workers.run`; the defaults are one
process and two threads. The Dramatiq hard timeout is independently configurable
and validation requires it to leave five seconds before lease expiry. Fixed-source
HTTP total and connect timeouts are also configurable and bounded.

## Transactions and observability

The claim commits before connector work starts. Connector changes and job success
commit together. A controlled failure rolls back connector work before the job
is marked queued or failed in a new transaction. Structured logs include event,
job ID, source ID, correlation ID, state and attempt; exception messages and
configuration secrets are excluded.

Redis is transport, not the job source of truth. PostgreSQL state supports
status reads, idempotency, retry exhaustion and restart recovery. Task 08 adds no
Kafka, microservice, LLM, RAG, arbitrary ingestion or public unauthenticated
write endpoint.

Task 14 retained one `ingestion` queue because only one approved job kind exists
and Redis enqueueing was more than ten times faster than first-pass object
processing. PostgreSQL persistence and deduplication are the measured limits.
See `docs/performance/pipeline-baseline.md` for the reproducible workload,
results and future scaling triggers.
