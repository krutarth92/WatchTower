# Task 10: evidence-grounded research RAG

Status: complete, reverified and approved.
Date: 2026-09-29.

## Prior-task verification

Task 09 was approved, inspected and revalidated before this task began. Exact
results are recorded in `task-09-search-baseline.md`; no required check remains
blocked.

## Mandatory decision

The user approved the recommended baseline on 2026-09-29: provider-neutral
adapters, no evidence/source text sent outside the machine, zero external-model
spend, pgvector, deterministic test providers, and a live endpoint disabled
until a real provider is explicitly configured. The required
`docs/design/system-workflow-reference.md` remains missing; its contents are not
inferred.

Approved baseline: keep provider adapters disabled by default, use pgvector
for evidence embeddings, expose the research path only to an authenticated
operator, and test the complete grounding contract with deterministic fake
providers. A real provider should be enabled only after the user selects either
a local runtime or an external API and states which evidence may leave the
machine plus a spending limit.

## Planned bounded implementation

1. Add pgvector infrastructure and evidence embeddings linked to evidence and
   source IDs, without arbitrary technical-artifact chunking.
2. Add deterministic intent classification for actor overview, behavior change
   and evidence-support questions.
3. Retrieve structured actor/timeline/evidence records with actor/time filters,
   vector similarity and retained provenance; rerank deterministically.
4. Allocate a configurable context budget and isolate untrusted retrieved text
   from system instructions.
5. Validate structured model output so citations reference retrieved records,
   OBSERVED and ASSESSED remain distinct, and unsupported output fails closed.
6. Add an authenticated, disabled-until-configured research endpoint and an
   evaluation set for recall, citations, unsupported claims, insufficient
   evidence and actor/time filtering.

Forecasting, autonomous/multiple agents, LangChain, Pinecone, OpenSearch,
frontend and unrelated tasks remain outside this task.

## Implementation result

- Added provider-neutral embedding and grounded-model protocols. No live model
  adapter or credential was added, and the application leaves the research
  service unconfigured by default.
- Added pgvector-backed `evidence_embeddings` with restrictive evidence/source
  links, content hashes, provider identity and dimensions. The indexer is
  idempotent and replaces a stale vector when evidence content changes.
- Implemented deterministic intent classification, actor/time-scoped retrieval,
  a relevance cutoff, stable reranking, adaptive context allocation and explicit
  untrusted-context isolation.
- Added fail-closed structured-output validation. Each claim must cite retrieved
  evidence and use an intelligence type present in its cited observation.
- Added the operator-only research API contract, retained source metadata and
  explicit model-interpretation labeling. Default configuration returns 503.
- Added the RAG evaluation fixture, integration coverage and design/setup docs.
  Technical artifacts remain unsplit and are deferred to their Task 11 model.

## Validation result

Validation was run against the live local pgvector/PostgreSQL and Redis Compose
services on 2026-09-29.

- `$env:UV_CACHE_DIR='.uv-cache'; .\.venv\Scripts\python.exe -m uv lock`:
  PASS, 44 packages resolved and pgvector 0.5.0 added.
- `$env:UV_CACHE_DIR='.uv-cache'; .\.venv\Scripts\python.exe -m uv sync
  --all-groups`: PASS; the locked project and pgvector installed.
- `.\.venv\Scripts\alembic.exe downgrade b7d9e1f3a5c2` then
  `.\.venv\Scripts\alembic.exe upgrade head`: PASS.
- `.\.venv\Scripts\alembic.exe heads` and `current`: PASS at
  `c8e2f4a6b9d1 (head)`.
- `.\.venv\Scripts\alembic.exe check`: PASS, no new upgrade operations detected.
- Database inspection: vector extension 0.8.6 and one
  `evidence_embeddings` table present.
- `.\.venv\Scripts\pytest.exe -q` with
  `WATCHTOWER_TEST_DATABASE_URL` set from the local development database: PASS,
  67 tests. The only warning is Starlette's existing notice
  that its httpx-backed TestClient compatibility layer is deprecated.
- `.\.venv\Scripts\ruff.exe check .`: PASS.
- `.\.venv\Scripts\ruff.exe format --check .`: PASS, 89 files formatted.
- `.\.venv\Scripts\pyright.exe`: PASS, zero errors and warnings.
- `git diff --check`: PASS. Git has no tracked baseline yet, so `git status`
  reports the repository files as untracked and no conventional diff is
  available.
- Docker Compose: PASS; `pgvector/pgvector:pg17` and `redis:7-alpine` healthy.
- Live API: `/health`, `/ready` and `/docs` returned 200; OpenAPI contains
  `/api/v1/operations/research/answers`. The locally running API was restarted
  from the current files.

## Acceptance review

- PASS: all three required question classes have explicit deterministic intents.
- PASS: the pipeline implements intent, retrieval, reranking, adaptive context,
  model boundary and validated grounded response stages.
- PASS: responses retain citations and source metadata, honor a configurable
  budget, support insufficient evidence and separate observed from assessed.
- PASS: retrieved source text is treated as untrusted data and remains separate
  from system instructions; invalid structured output fails closed.
- PASS: embeddings are stored in pgvector and linked to evidence/source IDs.
- PASS: the evaluation covers recall, correct citation membership, rejection of
  unsupported claims, insufficient evidence, actor isolation and time filters.
- PASS: normal reads/searches do not invoke models, and the live endpoint stays
  disabled until a provider is explicitly configured.
- PASS: no forecasting, agent orchestration, external vector service, frontend,
  or Task 11 artifact implementation was added.

## Concrete remaining risks

- There is no approved live local model, so no production answers or automatic
  embedding backfill are available. This is the intended approved boundary.
- Exact vector scans are appropriate only for the initial unmeasured corpus. A
  dimension-specific vector index requires an approved provider and performance
  evidence.
- The TestClient deprecation warning remains in upstream FastAPI/Starlette test
  plumbing and does not affect runtime behavior.

## Human review checkpoint

Task 10 was approved by the user's instruction to start the next task.

Transition verification on 2026-09-29 inspected the current execution record
and repository status. `git diff --check` passed; the repository still has no
tracked baseline, so files remain visible as untracked rather than as a normal
diff. `pytest -q tests/test_research_rag.py` passed all 5 tests, focused Ruff
passed, focused Pyright reported zero errors/warnings, Alembic remained at
`c8e2f4a6b9d1 (head)` with no schema drift, and the live `/ready` endpoint
returned 200. No Task 10 issue blocks Task 11.
