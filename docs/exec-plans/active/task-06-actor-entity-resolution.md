# Task 06: actor entity resolution

Status: complete, reverified and approved; Task 07 started.
Date: 2026-09-28.

## Prior-task verification

Task 05 was inspected and fully revalidated before this task began. The exact
commands, results and the user's approval are recorded in
`task-05-normalization-pipeline.md`. No required check remains blocked.

## Contract

`docs/design/actor-entity-resolution.md` defines safe exact rules, curated
mapping, candidate handling, source-conflict behavior, manual correction,
idempotency and audit semantics before implementation. The requested
`docs/design/system-workflow-reference.md` remains missing; no contents are
inferred.

## Implementation plan

1. Add curated known-alias and append-only resolution-decision models with an
   additive migration.
2. Implement conservative normalization, exact-rule resolution, fuzzy candidate
   discovery, source conflict detection and idempotent source Alias intake.
3. Add manual link/relink/unlink and curated-rule service boundaries with
   required reason, operator, confidence and optional evidence.
4. Test exact known alias, ambiguous similar name, conflicting assertions,
   manual correction, repeat resolution and duplicate-merge prevention.
5. Validate migration cycles, the complete suite, static checks and packaging.

No normalization remapping, public endpoint, worker, LLM, graph database or
unrelated task is in scope.

## Implementation

- Added curated alias rules with normalized lookup, explicit actor, reviewer,
  reason, confidence, optional Evidence and active state.
- Added append-only resolution decisions for automatic links, unresolved
  outcomes and manual link/relink/unlink. Each decision records method, current
  and previous Actor, reason, confidence, Evidence, operator, candidate snapshot,
  stable hash and database-generated sequence.
- Added deterministic NFKC/case-fold/whitespace name normalization. Exact
  canonical names and reviewed alias rules may auto-link only when all exact
  evidence identifies one Actor.
- Kept linked aliases from other sources as candidates only. Conflicting exact
  assertions remain unresolved; string similarity can surface up to ten review
  candidates and never changes an Alias link.
- Preserved Alias source label, source identity, native ID and metadata. Exact
  replay is idempotent; conflicting immutable source data raises an explicit
  error rather than overwriting the assertion.
- Added a transaction-scoped manual correction boundary and a reversible
  additive migration. The service flushes and leaves commit ownership to its
  caller.

## Files changed

- `alembic/versions/e4b8c1d2a6f0_add_actor_resolution_audit.py`
- `apps/api/src/watchtower/db/__init__.py`
- `apps/api/src/watchtower/db/models.py`
- `apps/api/src/watchtower/services/__init__.py`
- `apps/api/src/watchtower/services/actor_resolution.py`
- `docs/design/actor-entity-resolution.md`
- `docs/exec-plans/active/bootstrap.md`
- `docs/exec-plans/active/task-05-normalization-pipeline.md`
- `docs/exec-plans/active/task-06-actor-entity-resolution.md`
- `tests/test_actor_resolution.py`

## Validation performed

All database checks used the healthy local PostgreSQL 17 Compose service and
transaction-rolled-back test records. Redis was also healthy. No external source
or model was used.

| Command / check | Result |
| --- | --- |
| Focused `pytest -p no:cacheprovider tests/test_actor_resolution.py -q` with `WATCHTOWER_TEST_DATABASE_URL` | PASS: 6 tests |
| Full `pytest -p no:cacheprovider` with `WATCHTOWER_TEST_DATABASE_URL` | PASS: 41 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 51 files formatted |
| `pyright` | PASS: zero errors or warnings |
| `alembic downgrade d7a9b2f1c4e8` then `alembic upgrade head` | PASS after the final migration change |
| `alembic current` | PASS: `e4b8c1d2a6f0 (head)` |
| `alembic check` | PASS: no model/schema drift |
| `uv lock --check` with the workspace cache | PASS: 41 locked packages |
| `uv build --offline` and package inspection | PASS: service and migration included; runtime caches excluded |
| `docker compose ps` | PASS: PostgreSQL and Redis healthy |
| `git diff --check` | PASS |

The full suite reports one upstream Starlette TestClient deprecation warning;
it does not affect actor resolution.

## Acceptance criteria

- PASS: safe exact canonical-name rules auto-link and record a reason,
  confidence, candidates and audit method.
- PASS: reviewed known-alias mappings can auto-link and retain reviewer and
  optional evidence details.
- PASS: every source Alias remains a distinct record and keeps its original
  label and source metadata.
- PASS: similarity alone only emits unresolved candidates and cannot merge or
  create Actors.
- PASS: conflicting source assertions stay unresolved with every exact Actor
  candidate captured.
- PASS: manual link, relink and unlink preserve the source label and append
  selected and previous Actor details to the audit trail.
- PASS: unchanged automatic resolution and identical manual correction are
  idempotent and do not duplicate Alias or audit rows.
- PASS: tests cover exact known alias, ambiguous similar names, conflicting
  assertions, manual correction, repeated resolution and accidental-merge
  prevention.
- PASS: no LLM merger, graph database or source-label overwrite was introduced.

## Risks and unresolved issues

- Similarity candidate discovery scans Actors and curated rules in process. It
  is deliberately bounded to ten results but will need database-assisted
  retrieval if the actor catalog becomes large.
- Database uniqueness prevents duplicate source aliases and alias rules, but
  concurrent creators can still receive an integrity error and must retry at a
  higher transaction boundary.
- The required `docs/design/system-workflow-reference.md` is absent. No workflow
  contract was inferred from it.

## Scope and review checkpoint

No API endpoint, normalization remapping, ingestion worker, search, RAG, LLM,
graph database, external lookup, destructive migration or unrelated task was
implemented. No production data or Git commit was created.

Task 06 is complete. Stop here and obtain explicit human approval before Task 07.

## Task 07 transition verification

On 2026-09-28 the Task 06 design, migration, models, resolution service, audit
ordering and six required integration scenarios were inspected against the
current checkout. Final results were: `pytest -p no:cacheprovider` PASS (41
tests, one upstream Starlette warning), `ruff check .` PASS, `ruff format
--check .` PASS (51 files), `pyright` PASS with zero errors or warnings,
`alembic current` PASS at `e4b8c1d2a6f0 (head)`, `alembic check` PASS with no
drift, Docker Compose PostgreSQL and Redis healthy, and `git diff --check` PASS.
No required check remains skipped or blocked. The user's instruction to start
the next task satisfies the Task 06 human review checkpoint.
