# Task 02: core intelligence data model

Status: complete, verified and approved for Task 03.
Date: 2026-09-27.

## Prior-task verification

Task 01 verification is complete and recorded in
task-01-backend-foundation.md: clean install/build, 8 tests, lint, formatting,
types, online Alembic, healthy Compose services and real readiness recovery all
pass. The user's request to start the next task supplies the required review
approval. Task 02 began only after those results were recorded.

## Design gate

The data model was designed first in `docs/design/intelligence-data-model.md`.
Implementation and migration work follows that document. The missing original
system workflow reference is still explicitly unavailable; no contents are
assumed. This task follows the approved V1 scope and current AGENTS.md.

## Implementation

- `apps/api/src/watchtower/db/models.py` defines Source, RawEvidence, Actor,
  Alias, Observation, Evidence, Behavior, Technique, Campaign and Relationship,
  plus explicit association tables and observed/assessed and origin enums.
- `apps/api/src/watchtower/db/__init__.py` exports the model surface and loads
  model metadata for migrations.
- `alembic/versions/6a4cae0a31d9_create_core_intelligence_model.py` creates the
  complete schema, indexes, foreign keys, checks and shared PostgreSQL enums.
  Its downgrade reverses only this migration and drops its enum types last.
- `tests/test_models.py` covers the complete object lifecycle, unresolved and
  linked aliases, provenance, behavior/technique links, campaign relationship,
  chronological actor timeline, observed/assessed separation and invalid data.
- `docs/design/intelligence-data-model.md` records semantics, constraints,
  relationship scope, indexes and an example lifecycle.
- `SETUP.md` now describes the domain migration and located Docker installation.

## Validation performed

All database validation used the local PostgreSQL 17 Compose service and the
ignored development `.env`. No production or external database was contacted.

| Command / check | Result |
| --- | --- |
| `alembic downgrade base` | PASS: Task 02 schema removed cleanly |
| `alembic upgrade head` | PASS: revision 6a4cae0a31d9 applied |
| `alembic current` | PASS: 6a4cae0a31d9 (head) |
| `alembic check` | PASS: no new upgrade operations detected |
| `alembic upgrade head --sql` | PASS: valid offline creation SQL, shared enums created once |
| `alembic downgrade 6a4cae0a31d9:base --sql` | PASS: valid offline reversal SQL, enums dropped last |
| `pytest -p no:cacheprovider` with WATCHTOWER_TEST_DATABASE_URL | PASS: 14 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 23 files formatted |
| `pyright` | PASS: zero errors or warnings |
| SQLAlchemy database inspection | PASS: 15 expected tables including Alembic version table |
| `uv build` | PASS: source distribution and wheel |
| Package inspection with Python tarfile/zipfile | PASS: model and migration included; secret `.env`, local tools, environments and caches excluded |

The test suite reports one upstream Starlette TestClient deprecation warning;
it does not affect results. The cache provider was disabled to avoid an existing
local `.pytest_cache` permission warning unrelated to application behavior.

## Acceptance criteria

- PASS: create Actor and linked/unresolved Aliases without implied equivalence.
- PASS: create Source, RawEvidence reference and citable Evidence.
- PASS: create an Observation with mandatory Source and optional RawEvidence,
  plus explicit Evidence links.
- PASS: associate an Observation with an Actor, Behavior and Technique.
- PASS: create an evidence-backed Actor-to-Campaign Relationship.
- PASS: query actor observations chronologically using indexed time fields.
- PASS: database rejects blank required values, invalid SHA-256, confidence over
  100 and reversed campaign time ranges.
- PASS: imported observed facts and WATCHTOWER assessments remain separate rows
  with distinct enum values and provenance.
- PASS: migration upgrade/downgrade behavior is practical and non-destructive to
  objects outside this migration.

## Risks and limitations

- V1 Relationship is intentionally Actor-to-Campaign. Expanding it to arbitrary
  entities requires a later explicit design rather than unvalidated polymorphism.
- The database requires an Observation Source but cannot require a many-to-many
  Evidence row at insert time. Publishing/service logic must require evidence for
  important observations; the model preserves that link once supplied.
- RawEvidence is a reference model only. Task 03 owns processing state, intake
  idempotency details, licensing notes and object-storage behavior.
- Normalized-name generation is not implemented here; deterministic
  normalization belongs in Tasks 05–06. This task stores and constrains values.

## Scope and review checkpoint

No API endpoints, ingestion behavior, entity resolution, workers, RAG, frontend,
STIX export or production fixtures were added. PostgreSQL and Redis remain local
development services. No Git commit was created.

Task 02 requires stopping after schema, tests and design are complete. Verify
this task against the current files before Task 03, then obtain human approval.

Transition verification on 2026-09-27 reread AGENTS.md, this report and Task 03;
inspected Git status/diff; reran all 14 PostgreSQL-backed tests, Ruff lint and
format checks, Pyright, Alembic current and Alembic schema comparison. All passed
against the unchanged Task 02 files. The user then explicitly approved Task 02.
Task 03 may proceed.
