# Task 05: normalization pipeline

Status: complete, reverified and approved; Task 06 started.
Date: 2026-09-28.

## Prior-task verification

Task 04 was inspected and fully revalidated before this task began. Docker was
initially stopped; it was restored and every affected check was rerun. The exact
commands, results and the user's approval are recorded in
`task-04-mitre-attack-reference-connector.md`. No check remains blocked.

## Contract

`docs/design/normalization-pipeline.md` defines the stages, ATT&CK mapping,
status/error ledger, deduplication, timestamp and replay semantics before
implementation. The requested `docs/design/system-workflow-reference.md`
remains missing, so no contents are inferred.

## Implementation plan

1. Add the normalization ledger model and additive migration.
2. Implement explicit source parse, canonical normalize, validate, deduplicate
   and persist stages for ATT&CK intrusion-set observations.
3. Integrate the persistent emitter with the Task 04 connector boundary.
4. Test valid, malformed, duplicate, missing optional fields, replay, failed
   stages, unsupported records and provenance continuity using local fixtures.
5. Verify migrations, the complete suite, static checks, lock and package.

No actor resolution, techniques/campaign mapping, workers, API endpoints, LLMs,
embeddings or unrelated task is in scope.

## Implementation

- Added a durable `normalization_records` ledger keyed by raw evidence and
  object index. It records source/raw/native identity, exact canonical JSON
  payload hash, stage, status, bounded reason, attempts, processing time and the
  resulting Observation when one exists.
- Added explicit parse, normalize, validate, deduplicate and persist boundaries.
  The transaction-scoped pipeline implements the Task 04 emitter protocol and
  contains persistence work in a nested transaction.
- Added a strict ATT&CK STIX 2.1 intrusion-set parser and deterministic canonical
  observation normalizer. Timestamps require an offset and normalize to UTC;
  absent optional description and time-range fields receive documented defaults.
- Added source-scoped deduplication using the existing
  `(source_id, source_native_id)` Observation identity. Exact replay and older
  records retain the existing row, newer source timestamps update it, and equal
  timestamps with different canonical content are rejected as conflicts.
- Unsupported STIX types are recorded with a reason and do not fail the bundle.
  Malformed supported records and unexpected stage failures record their exact
  stage/status before propagating a controlled failure to raw processing.
- Added the reversible `d7a9b2f1c4e8` migration with enums, constraints, foreign
  keys and indexes for replay and operational inspection.

## Files changed

- `alembic/versions/d7a9b2f1c4e8_add_normalization_ledger.py`
- `apps/api/src/watchtower/db/__init__.py`
- `apps/api/src/watchtower/db/models.py`
- `apps/api/src/watchtower/ingestion/__init__.py`
- `apps/api/src/watchtower/ingestion/normalization.py`
- `apps/api/src/watchtower/ingestion/mitre_attack_normalization.py`
- `docs/data-sources/mitre-attack-enterprise.md`
- `docs/design/normalization-pipeline.md`
- `docs/exec-plans/active/bootstrap.md`
- `docs/exec-plans/active/task-04-mitre-attack-reference-connector.md`
- `docs/exec-plans/active/task-05-normalization-pipeline.md`
- `tests/test_normalization_pipeline.py`

## Validation performed

All database tests used the healthy local PostgreSQL 17 Compose service and
local inert fixtures. Redis was also healthy. No live source or model was used.

| Command / check | Result |
| --- | --- |
| `pytest -p no:cacheprovider` with `WATCHTOWER_TEST_DATABASE_URL` | PASS: 35 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 45 files formatted |
| `pyright` with bundled Node runtime on PATH | PASS: zero errors or warnings |
| `alembic downgrade 83c89c27e40c` then `alembic upgrade head` | PASS |
| `alembic current` | PASS: `d7a9b2f1c4e8 (head)` |
| `alembic check` | PASS: no model/schema drift |
| Offline upgrade and downgrade SQL for `83c89c27e40c` ↔ `d7a9b2f1c4e8` | PASS |
| `uv lock --check` | PASS: 41 locked packages |
| `uv build` and package inspection | PASS: pipeline and migration included; local runtime artifacts excluded |
| `docker compose ps` | PASS: PostgreSQL and Redis healthy |
| `git diff --check` | PASS |

The complete suite reports one upstream Starlette TestClient deprecation
warning; it does not affect normalization behavior.

## Acceptance criteria

- PASS: raw evidence flows through explicit parse, normalize, validate,
  deduplicate and persist stages into canonical Observations.
- PASS: source-specific parsing and canonical normalization are separate typed
  contracts with deterministic logic only.
- PASS: source, raw evidence and native identity survive every transformation
  and are asserted end to end.
- PASS: each record receives durable status, stage, attempts and a reason for
  rejection/failure; raw evidence remains intact.
- PASS: exact replay and duplicate source objects cannot create duplicate
  Observations; older records cannot overwrite newer source state.
- PASS: equal-timestamp canonical conflicts are rejected instead of being
  resolved by arrival order.
- PASS: timestamps normalize consistently to UTC and optional source fields stay
  optional with deterministic defaults.
- PASS: tests cover valid, malformed, duplicate, missing optional fields,
  replay, failed persistence, unsupported type, provenance continuity, older
  source versions and canonical conflicts.
- PASS: no LLM, embeddings or actor-identity inference was introduced.

## Risks and unresolved issues

- Only ATT&CK `intrusion-set` has approved canonical semantics. Technique,
  campaign and relationship objects remain durably rejected until their mapping
  and evidence semantics are reviewed.
- A newer source version updates the canonical Observation to point at its newer
  RawEvidence. Older immutable raw objects and ledger rows remain queryable, but
  first-class Observation revision history is deferred to Task 17.
- Concurrent runs for the same source-native ID can race at the database unique
  constraint. The nested transaction preserves the session and replay repairs
  the attempt; Task 08 must add durable job ownership before worker concurrency.

## Scope and review checkpoint

No actor/alias resolution, behavior/technique/campaign persistence, worker, API,
search, LLM, embedding, live source access, destructive migration or unrelated
task was implemented. No production data or Git commit was created.

Task 05 is complete. Stop here and obtain explicit human approval before Task 06.

## Task 06 transition verification

On 2026-09-28 the Task 05 schema, migration, pipeline, ATT&CK mapping,
documentation and tests were inspected against the current checkout. Final
results were: `pytest -p no:cacheprovider` PASS (35 tests, one upstream
Starlette warning), `ruff check .` PASS, `ruff format --check .` PASS (45
files), `pyright` PASS with zero errors or warnings, `alembic current` PASS at
`d7a9b2f1c4e8 (head)`, `alembic check` PASS with no drift, `uv lock --check`
PASS, `uv build` and package inspection PASS after approved network escalation,
Docker Compose PostgreSQL and Redis healthy, and `git diff --check` PASS. No
required check remains skipped or blocked. The user's instruction to start the
next task satisfies the Task 05 human review checkpoint.
