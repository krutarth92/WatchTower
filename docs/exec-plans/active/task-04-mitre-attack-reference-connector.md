# Task 04: MITRE ATT&CK reference connector

Status: complete, reverified and approved; Task 05 started.
Date: 2026-09-27.

## Prior-task verification

Task 03 was inspected and revalidated against the current checkout before this
task began. The exact results and the user's approval are recorded in
`task-03-source-registry-and-raw-evidence.md`. All required tests, lint, format,
type, migration-state, schema-drift and diff checks passed.

## Source decision

`docs/product-specs/v1-scope.md` explicitly selects a versioned MITRE ATT&CK
STIX dataset for the reference connector. No reviewed project document selects
another first connector. Source URL, format, usage policy, licensing, retrieval
safety and replay behavior are defined in
`docs/data-sources/mitre-attack-enterprise.md` before implementation.

The requested workflow reference remains missing; no contents are inferred.

## Implementation plan

1. Add the narrow STIX-object normalization boundary and fixture-backed tests.
2. Add a fixed-source HTTP fetcher with timeouts, redirect rejection, media-type
   validation and streaming byte limits.
3. Register MITRE provenance, store exact raw bytes, emit bounded envelopes and
   record processing outcomes and run metrics.
4. Verify success, malformed input, duplicate replay, interrupted replay,
   partial object failure and unavailable-source behavior.
5. Run the full test, lint, format, type and migration checks and record results.

No transformed intelligence persistence, universal connector framework, worker,
live-test dependency or arbitrary-URL fetch path is in scope.

## Implementation

- The source contract pins Enterprise ATT&CK 19.2 through its official `v19.2`
  release tag and records its STIX 2.1 format, release date, usage policy,
  license notice, retrieval controls and replay behavior.
- `MitreAttackFetcher` can request only the compiled-in source URL. It disables
  redirects, applies connect/read/write/pool timeouts, checks HTTP status and
  media type, enforces declared and streamed size limits, and returns bounded
  retrieval metadata without exposing upstream error bodies.
- `MitreAttackConnector` idempotently registers MITRE, writes exact bytes to the
  raw intake before parsing, records bundle/version/header metadata, validates
  the minimal STIX bundle/object structure, and emits provenance-bearing
  `NormalizationRecord` values through a narrow protocol.
- Successful duplicate bundles are skipped. Failed bundles are replayable, and
  abandoned `processing` records are recovered to `pending` before a new
  attempt. Malformed and partially failed bundles retain their raw evidence and
  finish with explicit failed state and bounded issues.
- Each run returns counts, byte size, duration, duplicate state and issues, and
  writes the same operational fields to structured JSON logs.
- HTTPX moved from the development-only group into runtime dependencies. The
  lock and both compatibility requirements exports were regenerated.

## Files changed

- `.env.example`
- `SETUP.md`
- `pyproject.toml`
- `uv.lock`
- `requirements.txt`
- `requirements-dev.txt`
- `apps/api/src/watchtower/core/logging.py`
- `apps/api/src/watchtower/ingestion/__init__.py`
- `apps/api/src/watchtower/ingestion/raw_evidence.py`
- `apps/api/src/watchtower/ingestion/normalization.py`
- `apps/api/src/watchtower/ingestion/mitre_attack.py`
- `docs/data-sources/mitre-attack-enterprise.md`
- `docs/exec-plans/active/bootstrap.md`
- `docs/exec-plans/active/task-03-source-registry-and-raw-evidence.md`
- `docs/exec-plans/active/task-04-mitre-attack-reference-connector.md`
- `tests/fixtures/mitre_attack/enterprise-attack-small.json`
- `tests/test_mitre_attack_connector.py`

The configuration and setup files retain the existing 10 MiB raw-evidence
default; they were reviewed and ultimately left semantically unchanged because
the pinned release fits within that bound.

## Validation performed

All database checks used the healthy local PostgreSQL 17 Compose service. Redis
was also healthy. Tests used inert local STIX fixtures and HTTPX mock transports;
the ordinary suite made no live source request.

| Command / check | Result |
| --- | --- |
| `pytest -p no:cacheprovider` with `WATCHTOWER_TEST_DATABASE_URL` | PASS: 27 tests |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS: 40 files formatted |
| `pyright` with the bundled Node runtime on PATH | PASS: zero errors or warnings |
| `alembic current` | PASS: `83c89c27e40c (head)` |
| `alembic check` | PASS: no model/schema drift |
| `uv lock --check` | PASS: 41 packages resolved from the lock |
| `uv build` | PASS: source distribution and wheel built |
| Package inspection | PASS: connector and boundary included; `.env`, `.tools` and runtime raw storage excluded |
| `docker compose ps` | PASS after approved sandbox escalation: PostgreSQL and Redis healthy |
| `git diff --check` | PASS |

The full suite reports one upstream Starlette TestClient deprecation warning;
it does not affect connector behavior.

## Acceptance criteria

- PASS: existing docs were checked and confirm MITRE ATT&CK as the first source.
- PASS: source URL/type, expected format, usage, license and replay are documented.
- PASS: one stable, tagged, machine-readable STIX source is fetched or read.
- PASS: retrieval and bundle metadata are recorded with exact raw evidence.
- PASS: source objects enter a narrow normalization boundary with source and raw
  evidence provenance; no transformed intelligence is persisted.
- PASS: run results and structured logs expose troubleshooting metrics and safe
  bounded failure details.
- PASS: content hashing, successful duplicate skipping, failed replay and
  interrupted-state recovery provide repeatable behavior.
- PASS: fixture tests cover success, malformed payload, duplicate ingestion,
  partial failure, interrupted replay and source unavailability.
- PASS: request timeouts, redirect rejection, media-type validation, declared
  and streamed size limits, and a fixed URL are implemented and tested.
- PASS: ordinary tests require no live internet and no HTML scraping or broad
  connector framework was introduced.

## Risks and unresolved issues

- The full upstream bundle was not downloaded during the deterministic test
  suite. The official release/index pages and tagged URL were checked, while
  live availability remains an upstream operational dependency.
- Recovery treats any preexisting `processing` state as interrupted. Task 08
  must add durable job ownership or leases before concurrent workers are
  enabled, otherwise simultaneous operator runs could emit the same boundary
  records.
- The normalization emitter is intentionally a protocol with fixture
  implementations. Task 05 must make its persistent implementation idempotent
  and contain per-object database errors so one rejected object cannot poison
  the surrounding session.

## Scope and review checkpoint

No HTML scraper, live-test requirement, transformed domain persistence,
normalization rules, worker, API endpoint, LLM integration, universal plugin
framework, schema migration or unrelated task was implemented. No production
data or Git commit was created.

Task 04 is complete. Stop here and obtain explicit human approval before Task 05.

## Task 05 transition verification

On 2026-09-28 the Task 04 implementation, documentation, fixture, tests,
dependency declarations and package contents were inspected again. Docker
Desktop was initially stopped, so database and package checks were not reported
as passed; the approved local runtime was restarted and every blocked command
was rerun. Final results were: Docker Compose PostgreSQL and Redis healthy,
`pytest -p no:cacheprovider` PASS (27 tests, one upstream Starlette warning),
`ruff check .` PASS, `ruff format --check .` PASS (40 files), `pyright` PASS
with zero errors or warnings, `alembic current` PASS at `83c89c27e40c (head)`,
`alembic check` PASS with no drift, `uv lock --check` PASS, `uv build` PASS,
package inspection PASS, and `git diff --check` PASS. No required check remains
skipped or blocked. The user's instruction to continue satisfies the Task 04
human review checkpoint.
