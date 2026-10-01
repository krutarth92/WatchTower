# Task 11: technical artifact handling

Status: complete, reverified and approved.
Date: 2026-09-29.

## Prior-task verification

Task 10 was approved, inspected and revalidated before this task began. Its
focused evaluation passed 5 tests, Ruff and Pyright passed, Alembic remained at
`c8e2f4a6b9d1 (head)` without drift, and live readiness returned 200. Exact
results are recorded in `task-10-evidence-rag-v1.md`.

## Context and constraints

The required `docs/design/system-workflow-reference.md` is still missing and its
contents will not be invented. The approved V1 scope, intelligence model, raw
evidence intake, normalization and RAG design documents govern this work.

Artifacts will be stored as faithful structured originals with raw/source
provenance. Validation results will be recorded without repairing or replacing
invalid originals. Small atomic STIX objects, Sigma rules and ATT&CK technique
references will not be split. Any large-artifact sectioning rule must be explicit
and deterministic.

## Planned bounded implementation

1. Define a technical-artifact schema for type, origin, canonical identity,
   validation status/errors, original structured content and provenance.
2. Add a reversible migration with duplicate constraints and searchable metadata.
3. Implement deterministic validation for STIX 2.1 objects/bundles, Sigma rules
   and ATT&CK technique references using approved reliable libraries where
   available, while always preserving the submitted original.
4. Implement idempotent ingestion linked to source/raw evidence and bounded
   retrieval/search contracts.
5. Add tests for valid/invalid STIX and Sigma, provenance, retrieval and
   duplicate handling, plus design/setup documentation.
6. Run migration round-trip, full tests, Ruff, formatting, Pyright, schema-drift
   and live API checks, then stop for human review.

## Implementation result

- Added `technical_artifacts` with exact source text, parsed JSONB structure,
  SHA-256 identity, validation outcome, imported/WATCHTOWER origin and restrictive
  source/raw-evidence provenance.
- Added official OASIS `stix2` parsing for standard STIX 2.1 and ATT&CK STIX,
  with explicit ATT&CK technique-reference checks. Added SigmaHQ pySigma parsing
  for atomic Sigma rules.
- Added idempotent internal ingestion that stores invalid content without repair,
  plus operator-only full-text metadata search and faithful ID retrieval.
- Kept STIX objects, bundles and Sigma rules atomic. No content is chunked;
  submissions above 10 MiB are rejected pending a reviewed format-specific rule.
- Added valid/invalid STIX and Sigma cases, a valid ATT&CK reference, imported
  provenance enforcement, WATCHTOWER origin, duplicate replay, retrieval/search,
  authentication and search-index coverage.

## Validation result

- `$env:UV_CACHE_DIR='.uv-cache'; .\.venv\Scripts\python.exe -m uv lock
  --check`: PASS, 59 packages resolved. Direct validator versions are pySigma
  1.5.1 and stix2 3.0.2.
- uv requirements exports: PASS; both compatibility files contain hash-pinned
  pySigma and stix2 entries and no discarded `stix2-validator` entry.
- `.\.venv\Scripts\alembic.exe downgrade c8e2f4a6b9d1` then
  `.\.venv\Scripts\alembic.exe upgrade head`: PASS.
- `.\.venv\Scripts\alembic.exe heads` and `current`: PASS at
  `d9f3a5b7c1e4 (head)`.
- `.\.venv\Scripts\alembic.exe check`: PASS, no new upgrade operations detected.
- `.\.venv\Scripts\pytest.exe -q` with the local PostgreSQL URL supplied through
  `WATCHTOWER_TEST_DATABASE_URL`: PASS, 72 tests. One existing Starlette
  TestClient deprecation warning remains.
- `.\.venv\Scripts\ruff.exe check .`: PASS.
- `.\.venv\Scripts\ruff.exe format --check .`: PASS, 97 files formatted.
- `.\.venv\Scripts\pyright.exe`: PASS, zero errors and warnings.
- `git diff --check`: PASS. The repository still has no tracked baseline, so
  files appear as untracked rather than in a conventional diff.
- Live API: `/health`, `/ready` and `/docs` returned 200. OpenAPI contains the
  artifact collection and ID-detail routes after restarting Uvicorn from the
  current files.

## Acceptance review

- PASS: exact STIX JSON and Sigma YAML source text survives validation/storage.
- PASS: standard STIX 2.1 objects and bundles validate through the OASIS library;
  invalid STIX is stored unchanged with controlled errors.
- PASS: Sigma rules validate through pySigma; invalid rules are stored unchanged.
- PASS: ATT&CK technique references require a STIX attack-pattern and MITRE ID.
- PASS: imported artifacts require matching raw/source provenance, while
  WATCHTOWER-generated artifacts carry an explicit origin flag.
- PASS: source-scoped type/content hashing makes duplicate ingestion idempotent.
- PASS: metadata is searchable and full original content is retrievable through
  bounded operator-only reads.
- PASS: no small artifact is chunked, no invalid source is repaired, and no
  Sigma rule is generated automatically.

## Concrete remaining risks

- The OASIS `stix2` object model enforces supported STIX structure and property
  semantics but does not emit the separate `stix2-validator` best-practice
  warnings. Its current installed wheel lacked required bundled schemas during
  evaluation, so it was not retained as a runtime dependency.
- pySigma parsing validates rule syntax and detection-condition structure. The
  optional SigmaHQ repository quality/style validator pack is not installed.
- Artifact ingestion is an internal service and is not yet wired into every
  connector/job. Automatic generation and a write API are intentionally absent.

## Human review checkpoint

Task 11 is complete and stopped for user approval. Task 12 has not started.

## Post-completion API verification

At the user's request, API behavior was rechecked on 2026-09-29 without changing
data. The API-focused PostgreSQL suite passed 37 tests. A live smoke matrix
exercised all 15 OpenAPI paths: health/readiness returned 200; empty actor and
global searches returned 200 with empty collections; all actor reads for an
unknown UUID returned the stable `actor_not_found` 404; an undersized search
query returned the documented 422; and all operator routes returned
`operator_auth_unavailable` 503 because the running local configuration has no
operator token. Response-contract assertions, request-ID propagation, Swagger
and OpenAPI checks passed. Database counts remained zero jobs and zero artifacts,
confirming that the smoke run performed no write. Authenticated success/error
paths remain covered transactionally by the passing API tests.

## Transition verification and approval

The user approved moving to the next task on 2026-09-29. Before Task 12 began,
the current Task 11 files and diff were inspected again. `git diff --check`
passed; the repository still has no tracked baseline, so the working tree is
reported as untracked rather than as a reviewable Git diff.

The focused artifact suite passed 5 tests, focused Ruff and Pyright checks
passed with no findings, Alembic reported `d9f3a5b7c1e4 (head)` with no model
drift, and live `/ready` returned 200. The artifact route remained present in
the live OpenAPI document. Task 11 therefore passed its transition gate with no
remaining blocker.
