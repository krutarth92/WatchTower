# Task 12: STIX 2.1 export

Status: complete, reverified and approved.
Date: 2026-09-29.

## Prior-task verification

Task 11 was approved by the user and reverified before this task began. The
focused artifact suite passed 5 tests, Ruff and Pyright passed, Alembic remained
at `d9f3a5b7c1e4 (head)` without drift, live readiness returned 200, and the
artifact API remained present in OpenAPI. The exact transition record is in
`task-11-technical-artifact-handling.md`.

## Instruction and scope review

Read `Instructions/TASK_12_STIX_2_1_EXPORT.md`, the V1 scope, the intelligence
data model and technical artifact design. The referenced
`docs/design/system-workflow-reference.md` is still absent; this known source
gap does not prevent the task-specific mapping from being made explicit.

Task 12 will export a bounded actor-centered intelligence view as STIX 2.1. It
will not change the internal model, add a database migration, invent custom STIX
types or properties, or represent WATCHTOWER assessments as observations.

## Planned implementation

1. Define and review the mapping, exclusions, stable identifier scheme,
   timestamp rules, confidence handling and provenance behavior in
   `docs/design/stix-mapping.md` before code changes.
2. Implement an internal export service that builds a deterministic STIX 2.1
   bundle for a canonical actor and its explicitly linked supported entities.
3. Add an operator-only read endpoint returning the bundle as
   `application/stix+json`.
4. Add validator-backed tests using the installed OASIS `stix2` object model,
   plus mapping, provenance, stable-ID, authorization and error-path coverage.
5. Run focused tests and static checks, the full suite, Alembic drift/current
   checks, and a live API smoke check before stopping for review.

## Implementation result

- Added the design-first mapping at `docs/design/stix-mapping.md`, including
  supported entities, exclusions, identifier rules, timestamps, confidence and
  provenance.
- Added a read-only export service for an actor-centered bundle. It emits
  standard intrusion-set, campaign, attack-pattern, note and relationship
  objects, validates the complete bundle with the OASIS `stix2` object model,
  and returns stable UUIDv5 IDs and deterministic ordering.
- Added the operator-only
  `GET /api/v1/operations/exports/stix/actors/{actor_id}` endpoint with the
  `application/stix+json` media type and stable actor-not-found handling.
- Added integration tests for standard validation, stable output, aliases,
  source/evidence references, confidence, timestamps, observed/assessed note
  separation, approved relationship direction, unsupported-predicate exclusion,
  authentication, media type, error handling and OpenAPI.

## Validation result

- `.\.venv\Scripts\pytest.exe -q tests/test_stix_export.py` with the local
  PostgreSQL URL supplied through `WATCHTOWER_TEST_DATABASE_URL`: PASS, 2 tests.
- `.\.venv\Scripts\pytest.exe -q` with the same database configuration: PASS,
  74 tests. One existing Starlette TestClient/httpx deprecation warning remains.
- `.\.venv\Scripts\ruff.exe check .`: PASS.
- `.\.venv\Scripts\ruff.exe format --check .`: PASS, 103 files formatted.
- `.\.venv\Scripts\pyright.exe`: PASS, zero errors and warnings.
- `.\.venv\Scripts\alembic.exe heads` and `current`: PASS at
  `d9f3a5b7c1e4 (head)`.
- `.\.venv\Scripts\alembic.exe check`: PASS, no new upgrade operations.
- `git diff --check`: PASS. The repository still has no tracked baseline, so
  files appear as untracked rather than in a conventional diff.
- Live API after restart: `/ready` and `/docs` returned 200; OpenAPI contains the
  export route and `application/stix+json` success media type. The unauthenticated
  live request returned the expected `operator_auth_unavailable` 503 because no
  operator token is configured in the local server. Authenticated export success
  and 404 behavior passed in the transactionally isolated API test.

## Acceptance review

- PASS: the complete export parses as STIX 2.1 with custom content disabled.
- PASS: stable entity, derived-relationship and bundle IDs are deterministic.
- PASS: the mapping and its deliberate limitations are documented first.
- PASS: the internal relational model is unchanged; no migration was added.
- PASS: source-native IDs, safe URLs, citations and excerpts retain provenance,
  while confidence and applicable timestamps preserve their original meaning.
- PASS: observed and assessed intelligence remain distinct note labels, and no
  assessment is emitted as STIX Observed Data.
- PASS: a read-only operator endpoint and internal service expose the approved
  actor-centered subset.
- PASS: validator-backed semantic and API tests cover the approved subset.

## Concrete remaining risks

- The OASIS `stix2` object model enforces object/property structure and rejects
  custom content, but this project does not include the separate
  `stix2-validator` best-practice warning rules.
- The approved subset does not export indicators, generic behaviors, cyber
  observables, arbitrary relationship predicates, or records that are not
  explicitly linked to the requested actor. These require separate reviewed
  mappings if the internal model later gains exact semantics for them.
- `docs/design/system-workflow-reference.md` remains absent, as it was before
  this task. The export mapping therefore relies on the available V1 scope and
  intelligence-model documents.

## Human review checkpoint

Task 12 is complete and stopped for user approval. Task 13 has not started.

## Transition verification and approval

The user approved moving to the next task on 2026-09-29. Before Task 13 began,
the current exporter, endpoint, tests and execution records were inspected.
`git diff --check` passed; the repository still has no tracked baseline, so its
files remain reported as untracked rather than as a conventional diff.

The focused STIX export suite passed 2 tests, focused Ruff and Pyright checks
passed, Alembic remained at `d9f3a5b7c1e4 (head)` with no drift, live readiness
returned 200, and OpenAPI still exposed the route with
`application/stix+json`. Task 12 therefore passed its transition gate with no
remaining blocker.
