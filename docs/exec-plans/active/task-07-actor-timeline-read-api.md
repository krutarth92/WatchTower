# Task 07: actor timeline read API

Status: complete, reverified and approved; Task 08 started.
Date: 2026-09-28.

## Prior-task verification

Task 06 was inspected and fully revalidated before this task began. The exact
commands, results and the user's approval are recorded in
`task-06-actor-entity-resolution.md`. No required check remains blocked.

## Contract

`docs/design/actor-timeline-read-api.md` defines the routes, response and error
shapes, cursor semantics, filters, request IDs, query strategy and response
limits before implementation. The required
`docs/design/system-workflow-reference.md` remains missing; no contents are
inferred.

## Implementation plan

1. Add versioned Pydantic response/error models and request-ID/error handling.
2. Implement read-only actor lookup, bounded name/alias search and alias reads.
3. Implement keyset-paginated observation/timeline reads with date/type filters
   and eager-loaded evidence and associations.
4. Add distinct behavior/technique and source/evidence reference reads.
5. Test the required behaviors, query-count bounds, OpenAPI and response limits,
   then run the complete validation suite and package checks.

No public write, ingestion job, RAG, LLM, Redis cache, frontend or unrelated
task is in scope.

## Implementation

- Added seven `/api/v1/actors` read routes for stable-ID lookup, bounded
  canonical/alias search, aliases, observations, timeline events,
  behavior/technique associations and source/evidence references.
- Added explicit Pydantic response models and one stable error envelope for
  resource, validation, routing and unexpected failures. OpenAPI documents the
  routes and response models.
- Added safe caller-provided or generated request IDs to every response and
  structured completion/error logs.
- Added opaque checksum-protected keyset cursors over descending
  `(observed_at, id)`. Cursors are scoped to Actor and date/type filters, pages
  fetch one extra row instead of counting, and limits are bounded from 1 to 100.
- Added inclusive timezone-aware date filters and observed/assessed filtering.
- Added fixed-query eager loading for Source, Evidence, Behavior and Technique
  relationships. Nested and collection outputs have deterministic ordering,
  explicit limits and truncation flags.
- Kept the API strictly read-only and database-backed without an LLM, RAG call,
  Redis cache or new dependency.

## Files changed

- `SETUP.md`
- `apps/api/src/watchtower/api/errors.py`
- `apps/api/src/watchtower/api/request_id.py`
- `apps/api/src/watchtower/api/v1/__init__.py`
- `apps/api/src/watchtower/api/v1/actors.py`
- `apps/api/src/watchtower/api/v1/router.py`
- `apps/api/src/watchtower/api/v1/schemas.py`
- `apps/api/src/watchtower/main.py`
- `apps/api/src/watchtower/services/actor_read.py`
- `docs/design/actor-timeline-read-api.md`
- `docs/exec-plans/active/bootstrap.md`
- `docs/exec-plans/active/task-06-actor-entity-resolution.md`
- `docs/exec-plans/active/task-07-actor-timeline-read-api.md`
- `tests/test_actor_read_api.py`

## Validation performed

All database tests used the healthy local PostgreSQL 17 Compose service and
transaction-rolled-back fixtures. No external source, model or cache was used.

| Command / check | Result |
| --- | --- |
| Focused `pytest -p no:cacheprovider tests/test_actor_read_api.py -q` with `WATCHTOWER_TEST_DATABASE_URL` | PASS: 8 tests |
| Full `pytest -p no:cacheprovider` with `WATCHTOWER_TEST_DATABASE_URL` | PASS: 49 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 61 files formatted |
| `pyright` | PASS: zero errors or warnings |
| `alembic current` | PASS: `e4b8c1d2a6f0 (head)` |
| `alembic check` | PASS: no model/schema drift; Task 07 adds no migration |
| `uv lock --check` with the workspace cache | PASS: 41 locked packages |
| `uv build --offline` and package inspection | PASS: Task 07 modules included; runtime caches excluded |
| Live Uvicorn `/health` and `/openapi.json` smoke check | PASS: HTTP 200, request ID present, seven actor paths |
| `git diff --check` | PASS |

The query-count test fetched one and four timeline events using the same bounded
number of SQL statements (no more than six). The full suite reports one upstream
Starlette TestClient deprecation warning; it does not affect the API behavior.

## Acceptance criteria

- PASS: stable-ID lookup and bounded canonical-name/source-alias search are
  available under `/api/v1`.
- PASS: source-preserved aliases, observations, timelines,
  behavior/technique associations and source/evidence references are exposed.
- PASS: every route has Pydantic response models and OpenAPI documentation.
- PASS: errors use a stable code/message/request-ID/details envelope.
- PASS: observations and timeline use filter-scoped keyset cursors with bounded
  page sizes and inclusive date/type filters.
- PASS: every response carries a correlation ID that is also written to request
  logs.
- PASS: fixed-count eager loading prevents relationship-driven N+1 growth.
- PASS: tests cover happy path, not found, alias lookup, pagination, altered
  cursor, date/type filter, empty timeline, evidence links, associations,
  OpenAPI and query-count sanity.
- PASS: ordinary reads invoke no LLM and no Redis cache was introduced.

## Risks and unresolved issues

- Substring name/alias search uses relational matching. It is intentionally
  capped, but Task 09 must provide indexed full-text ranking for a larger corpus.
- Association/reference collections report truncation but do not yet offer their
  own cursors; observation and timeline pages are fully cursor-paginated.
- Authentication and publication-state filtering do not exist yet. The server
  remains localhost-only and must not be exposed publicly until later security,
  publication and deployment tasks establish that boundary.
- The required `docs/design/system-workflow-reference.md` is absent. No workflow
  contract was inferred from it.

## Scope and review checkpoint

No public write, ingestion job, worker, full-text search, RAG, LLM, Redis cache,
frontend, deployment configuration, destructive migration or unrelated task was
implemented. No production data or Git commit was created.

Task 07 is complete. Stop here and obtain explicit human approval before Task 08.

## Task 08 transition verification

On 2026-09-28 the Task 07 API contract, routes, response/error models, cursor
logic, request IDs, eager-loading queries, tests and setup guidance were
inspected against the current checkout. Final results were: `pytest -p
no:cacheprovider` PASS (49 tests, one upstream Starlette warning), `ruff check
.` PASS, `ruff format --check .` PASS (61 files), `pyright` PASS with zero
errors or warnings, `alembic current` PASS at `e4b8c1d2a6f0 (head)`, `alembic
check` PASS with no drift, live `/health` and `/openapi.json` PASS with a request
ID and seven actor paths, Docker Compose PostgreSQL and Redis healthy, and `git
diff --check` PASS. No required check remains skipped or blocked. The user's
instruction to start the next task satisfies the Task 07 human review checkpoint.
