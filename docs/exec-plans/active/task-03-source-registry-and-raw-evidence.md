# Task 03: source registry and raw evidence

Status: complete, reverified and approved; Task 04 started.
Date: 2026-09-27.

## Prior-task verification

Task 02 was reverified on the current files and explicitly approved by the user.
The transition record is in task-02-core-intelligence-data-model.md. All 14 tests,
Ruff, formatting, Pyright, migration head and schema comparison passed before
Task 03 began.

## Contract

`docs/design/raw-evidence-intake.md` defines source registration, connector input,
idempotency, versioning, storage safety, transaction ownership and processing
state before implementation. The original system workflow reference remains
unavailable; no missing content is inferred.

## Implementation

- Source gains optional policy notes, license name and license URL.
- RawEvidence gains source location, unique object key, sanitized filename,
  content size, retrieval status, processing state/error/attempts and processing
  timestamp. Existing Task 02 reference columns remain intact.
- `SourceRegistration` and `RawEvidenceSubmission` reject unknown fields and
  validate URLs, JSON metadata, media types, timestamps and source locations.
- `SourceRegistry` idempotently registers identical sources and rejects silent
  changes to an existing source's immutable registration details.
- `RawEvidenceIntake` enforces size, hashes exact bytes, chooses deterministic
  source-scoped object keys, flushes idempotent rows and exposes explicit replay
  state transitions without taking transaction ownership from the caller.
- `ObjectStore` is a portable protocol. `LocalObjectStore` confines objects to a
  configured root, rejects traversal and unsafe segments, writes atomically,
  verifies collisions and never executes submitted content.
- The additive migration `83c89c27e40c` creates shared status enums, columns,
  constraints, indexes and a unique storage-key constraint.

## Validation performed

All database checks used the local PostgreSQL 17 Compose service. Filesystem
tests used isolated pytest temporary directories, never the repository or user
files. Test content was inert fixture data.

| Command / check | Result |
| --- | --- |
| `pytest -p no:cacheprovider` with WATCHTOWER_TEST_DATABASE_URL | PASS: 20 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 35 files formatted |
| `pyright` | PASS: zero errors or warnings |
| `alembic downgrade 6a4cae0a31d9` then `upgrade head` | PASS |
| `alembic current` | PASS: 83c89c27e40c (head) |
| `alembic check` | PASS: no model/schema drift |
| Offline upgrade/downgrade SQL for 6a4cae0a31d9 ↔ 83c89c27e40c | PASS |
| Upgrade with a preexisting Task 02 RawEvidence row | PASS: row preserved; safe status defaults backfilled |
| `uv build` and tar/wheel inspection | PASS: Task 03 code/migration included; secrets, raw data and local tools excluded |
| Git ignore checks | PASS: `.env`, `/storage/`, `.tools/` ignored |

The full suite reports one upstream Starlette TestClient deprecation warning;
it does not affect Task 03 behavior. The final database remains at migration head.

## Acceptance criteria

- PASS: source registration preserves policy/licensing metadata and is idempotent.
- PASS: new raw evidence stores exact bytes outside PostgreSQL with SHA-256,
  source/fetch/publication/MIME metadata and an immutable reference.
- PASS: duplicate bytes for one source reuse the row and object; a missing local
  object is repaired from the repeated submission.
- PASS: changed bytes create a new version; identical bytes from distinct sources
  retain separate provenance and source-scoped keys.
- PASS: invalid JSON metadata, timestamps, media types, control characters,
  unknown sources and oversized content are rejected.
- PASS: filenames and keys cannot traverse directories; unsafe keys, oversize
  storage writes and different-content collisions fail.
- PASS: pending/processing/succeeded/failed state, failure reason, attempts and
  reprocessing transitions are recorded and tested.
- PASS: raw bytes remain separate from normalized intelligence and are never run.

## Risks and limitations

- The local adapter is suitable for one development host. Production/multi-host
  deployment still needs an `ObjectStore` implementation backed by approved
  S3-compatible storage and its access/retention policy.
- If a database transaction rolls back after object creation, an unreferenced
  content-addressed object may remain. It is harmless and safely reusable; a
  future maintenance job may garbage-collect proven unreferenced objects.
- Retrieval failure before bytes exist is a connector/job concern and does not
  create a RawEvidence row. The retrieval status field records persisted object
  retrieval outcome; Task 04 will log source-unavailable failures.
- Processing transitions are synchronous service operations in Task 03. Task 08
  will coordinate them through durable jobs and worker retries.

## Scope and review checkpoint

No live connector, scraping, parsing, normalization, LLM, worker, public write
endpoint or broad plugin framework was added. No production data or Git commit
was created.

Task 03 requires stopping after stable tested intake. Verify these results again
before Task 04 and obtain explicit human approval.

## Task 04 transition verification

On 2026-09-27, immediately before Task 04 work began, the actual Task 03 files
and diff were inspected and the required checks were rerun against the current
checkout. PostgreSQL 17 and Redis were healthy in Docker Compose. The results
were: `pytest -p no:cacheprovider` PASS (20 tests, one upstream Starlette
deprecation warning), `ruff check .` PASS, `ruff format --check .` PASS (35
files), `pyright` PASS (zero errors or warnings), `alembic current` PASS at
`83c89c27e40c (head)`, `alembic check` PASS with no model/schema drift, and
`git diff --check` PASS. No required check was skipped or blocked. The user's
instruction to continue with the next task satisfied Task 03's human review
checkpoint.
