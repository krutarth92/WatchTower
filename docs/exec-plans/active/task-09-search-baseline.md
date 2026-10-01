# Task 09: deterministic PostgreSQL search baseline

Status: complete, reverified and approved; Task 10 planning started.
Date: 2026-09-29.

## Prior-task verification

Task 08 was approved by the user's request to start the next task, inspected and
revalidated before Task 09 began. Exact current-state results are recorded in
`task-08-async-ingestion-jobs.md`; no required check remains blocked.

## Contract and plan

`docs/search/search-baseline.md` defines the searchable entities, query parser,
index documents, ranking, filters, response and limitations. The required
`docs/design/system-workflow-reference.md` remains missing; its contents are not
inferred.

1. Add reversible GIN full-text expression indexes for the seven approved
   entity tables.
2. Implement one bounded union search service with deterministic ranking and
   stable tie-breaking.
3. Add the read-only `/api/v1/search` contract and validated filters.
4. Add a curated evaluation dataset and PostgreSQL integration tests for every
   required search mode and ranking sanity.
5. Run migration, API, evaluation, lint, formatting and type validation; record
   measured results and stop for human review.

No embedding, pgvector, RAG, LLM, OpenSearch, Elasticsearch, public write,
frontend or unrelated task is in scope.

## Implementation result

- Added seven additive GIN expression indexes over weighted PostgreSQL
  `tsvector` documents for actors, aliases, campaigns, behaviors, techniques,
  observations and sources.
- Added a single-query `UNION ALL` search service with exact-match boosts,
  `websearch_to_tsquery`, cover-density ranking, stable tie-breaking, relational
  source filters and bounded summaries/results.
- Added `GET /api/v1/search` with entity, source, intelligence type, date and
  limit filters plus a typed cross-entity response.
- Added an 11-case curated evaluation dataset and integration coverage for
  exact, alias, campaign, behavior, technique ID, keyword, quoted phrase,
  metadata, source, intelligence-type and date searches.
- Documented search fields, ranking, filters, operational use and explicit
  limitations without adding a new dependency or service.

## Validation and acceptance

Validation used the local PostgreSQL service on 2026-09-29:

- `WATCHTOWER_TEST_DATABASE_URL=<local .env URL> .venv/Scripts/python.exe -m pytest -q`
  — PASS, 62 tests; one Starlette deprecation warning.
- Curated evaluation — PASS, 11/11 expected entities ranked first with stable
  repeated ordering.
- `.venv/Scripts/ruff.exe check .` — PASS.
- `.venv/Scripts/ruff.exe format --check .` — PASS, 81 files formatted.
- `.venv/Scripts/pyright.exe` — PASS, zero errors/warnings.
- `alembic downgrade f2c4d6e8a1b3` then `alembic upgrade head` — PASS.
- `alembic current`, `heads` and `check` — PASS; current and sole head
  `b7d9e1f3a5c2`, no model drift.
- Offline `f2c4d6e8a1b3:b7d9e1f3a5c2` SQL — PASS, seven GIN index statements.
- `UV_CACHE_DIR=.uv-cache ... python -m uv lock --check` — PASS, 43 packages.
- Index inventory and EXPLAIN integration test — PASS; all seven indexes exist
  and the actor full-text predicate can use its GIN index.
- Live `/docs`, `/ready` and `/api/v1/search?q=attack&limit=5` — HTTP 200 with
  request-ID propagation. The development database currently has no matching
  `attack` records, so the live result list is correctly empty.

Acceptance criteria:

- PASS: actor names, aliases, campaigns, behaviors, techniques, observation
  text/metadata and source names/metadata are searchable.
- PASS: PostgreSQL relational queries and full-text GIN indexes provide the
  baseline; ranking and filters are documented and tested.
- PASS: exact lookup, alias lookup, keyword, quoted phrase, filters and ranking
  sanity have a checked-in curated evaluation.
- PASS: results and summaries are bounded and deterministic for equal scores.
- PASS: no embeddings, LLM, RAG, OpenSearch or Elasticsearch were added.

## Remaining issues and checkpoint

The 11-case fixture establishes regression behavior but does not measure
production-scale recall, ranking quality or latency. English stemming has no
typo tolerance and can miss non-English or punctuation-heavy technical terms.
Metadata text can match JSON keys as well as string values. The additive GIN
indexes are built normally rather than concurrently, so a future production
deployment with large populated tables must plan migration lock time. Search
has no publication or per-user visibility model and must remain locally bound
until the later publication/security tasks establish one.

The required `docs/design/system-workflow-reference.md` is still unavailable;
its contents were not inferred.

Task 09 is complete. Stop here and obtain explicit human approval before Task
10, as required by `Instructions/TASK_09_SEARCH_BASELINE.md` and the root
`AGENTS.md` transition rule.

## Task 10 transition verification

The user's 2026-09-29 request to continue satisfies Task 09's human review
checkpoint. Before Task 10 work, the actual search service, API, schemas,
migration, evaluation dataset, tests and documentation were inspected again.
The required workflow reference remains missing and no contents were inferred.

Current-state verification passed:

- `WATCHTOWER_TEST_DATABASE_URL=<local .env URL> .venv/Scripts/python.exe -m pytest tests/test_search.py -q`
  — 3 passed; all 11 curated cases run by the focused suite.
- Focused Ruff check/format — passed; five files formatted.
- Focused Pyright — zero errors/warnings.
- `alembic current` and `alembic check` — current at `b7d9e1f3a5c2` with no
  model drift.
- Live `/ready` and `/api/v1/search?q=attack&limit=5` — HTTP 200.

All Task 09 deliverables and acceptance criteria still pass. Its documented
relevance, language, metadata, migration-lock and visibility limitations remain
visible and do not invalidate the baseline. Task 10 planning may proceed.
