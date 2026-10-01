# Task 17: Living intelligence backend contract

Status: complete, reverified and approved; Task 18 started.
Date: 2026-10-01.

## Prior-task verification

Task 16 was explicitly approved and reverified against the current files before
this task began. Static checks, the full PostgreSQL-backed suite, package build,
migration state, Docker image build and non-root runtime smoke check passed. The
exact commands and the unchanged hosted-CI limitation are recorded in the Task
16 execution plan.

## Context and decisions

The approved V1 scope requires drafts to remain private and public reads to
expose only explicitly published advisories. Existing Evidence, Actor, Campaign,
Technique and `IntelligenceType` records remain canonical and will be linked,
not copied. `docs/design/system-workflow-reference.md` remains absent and its
contents are not inferred.

Use an immutable, append-only editorial model:

1. `Advisory` owns a stable slug and points to its currently published revision.
2. `AdvisoryRevision` stores a complete immutable editorial snapshot. New edits
   create a numbered revision; no update endpoint mutates an older snapshot.
3. Typed revision sections carry `observed` or `assessed` explicitly. Evidence
   and Actor/Campaign/Technique associations are revision-scoped so history is
   reproducible.
4. `AdvisoryUpdate` is an append-only, timestamped, sequenced event tied to the
   published revision context, with its own intelligence type and evidence.
5. Operator-token routes create revisions, publish one explicitly and append
   updates. Public routes filter publication state in SQL and expose bounded,
   deterministic update/revision history.

## Implementation plan

1. Add SQLAlchemy models and a reversible Alembic migration with integrity,
   uniqueness, foreign-key and public-read indexes.
2. Add strict request/response contracts and an atomic service for reference
   validation, additive revisioning, publication and append-only updates.
3. Add operator writes and public list/detail/revision/update reads under
   `/api/v1`, preserving the existing error and request-ID contract.
4. Add database-backed service/API tests for creation, evidence/entity links,
   publication filtering, update history and prior-revision preservation.
5. Document the stable contract, apply/reverse/reapply the migration, run the
   full suite and static checks, then stop for human review.

## Acceptance record

Implementation is complete:

- Added immutable advisory revisions, ordered intelligence-typed sections,
  revision-scoped evidence/entity links and append-only sequenced updates.
- Added token-protected create/revise/publish/update routes and published-only
  list/detail/revision/update public reads.
- Added the reversible `0218f83cad8e` migration with publication, uniqueness,
  reference and public-read constraints/indexes.
- Documented the stable backend contract and setup entry points. No frontend or
  automatic editorial generation was added.

Validation on 2026-10-01:

- `.venv\Scripts\alembic.exe downgrade a1c3e5f7b9d2` — passed.
- `.venv\Scripts\alembic.exe upgrade head` — passed.
- `.venv\Scripts\alembic.exe heads` and `current` — one head/current at
  `0218f83cad8e`.
- `.venv\Scripts\alembic.exe check` — no new upgrade operations.
- `.venv\Scripts\alembic.exe upgrade head --sql` — passed.
- `.venv\Scripts\pytest.exe -q tests/test_advisories.py` with the local
  PostgreSQL test URL — 2 passed.
- `.venv\Scripts\pytest.exe -q` with the local PostgreSQL test URL — 85
  passed; the existing Starlette TestClient deprecation warning remains.
- `.venv\Scripts\ruff.exe check .` — passed.
- `.venv\Scripts\ruff.exe format --check .` — 125 files formatted.
- `.venv\Scripts\pyright.exe` — 0 errors, 0 warnings.
- Restarted Uvicorn and Dramatiq against the migrated database. `/health`
  returned `ok`, `/ready` returned `ready`, OpenAPI contained the advisory
  detail route, the empty published list returned successfully, and PostgreSQL
  and Redis remained healthy.

Acceptance criteria:

- Create advisory: pass.
- Add a timestamped, evidence-linked update: pass.
- Preserve earlier state and published revision history: pass.
- Attach evidence: pass.
- Link actor, campaign and technique: pass.
- Published public read response with visible OBSERVED/ASSESSED types: pass.
- Draft and unpublished revision privacy: pass.
- Machine-readable bounded update history: pass.
- Backend contract documented and frontend left unchanged: pass.

Concrete remaining risk: publication is durable. A previously published
revision stays publicly readable even after a later revision is selected. A
future withdrawal/redaction policy needs an explicit audited state transition;
it must not be implemented as destructive history editing.

## Transition verification before Task 18

The user approved transition on 2026-10-01. The actual contracts, service,
routes, models, migration, tests and design document were inspected again.
`.venv\Scripts\ruff.exe check .`, formatting over 125 files and Pyright all
passed. The full PostgreSQL-backed suite passed 85 tests with the existing
Starlette TestClient deprecation warning. Alembic heads/current/check confirmed
the single current head `0218f83cad8e` with no model drift. The running API
returned `ok` and `ready`. No Task 17 acceptance issue remained, so Task 18
could start.
