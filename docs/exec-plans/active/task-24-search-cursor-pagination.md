# Task 24: deterministic search cursor pagination

Status: complete, verified and approved; Task 25 decision phase started.
Date: 2026-10-01.
Source: remaining V1 readiness gap G12.

## Prior-task verification

Task 23 was reinspected before this task began. Local and remote `main` matched
`998005c232189476ebddbc67d0dfd92d7ac70611` with a clean tree. The `httpx2`
development dependency, separate production `httpx` dependency, fatal-warning
pytest policy and active TestClient backend matched the accepted implementation.
Ruff, Pyright, uv lock and diff checks passed. Main CI run
[#24](https://github.com/krutarth92/WatchTower/actions/runs/36876326569)
passed all three required jobs. The user's next-task request satisfied Task 23's
review checkpoint.

## Goal and boundary

Add opaque keyset pagination to public cross-entity search over the existing
stable order: score descending, entity-type priority, case-folded title and UUID.
Bind cursors to the cleaned query and every result-shaping filter so they
cannot be reused against a different search scope.

Preserve current ranking, publication filtering, query semantics, maximum page
size and result fields. Do not add offset pagination, a count query, fuzzy
matching, a new index or a database migration.

## Acceptance criteria

- The API accepts an optional bounded cursor and returns `next_cursor` only when
  another result exists.
- Pages use `limit + 1` keyset retrieval over score/type/title/UUID and neither
  repeat nor skip results across equal-score and equal-title ties.
- The cursor includes a version, exact sort position and fingerprint of the
  cleaned query, selected entity types, source, intelligence and date filters.
- Malformed, altered and cross-scope cursors return the stable 422 validation
  envelope without exposing cursor contents.
- Existing relevance ordering and publication visibility tests continue to
  pass, with focused regression coverage for complete pagination.
- The full warning-free suite, Ruff, formatting, Pyright, Alembic and hosted
  protected-branch checks pass.

## Validation record

- PASS: focused search suite, 6 tests. Pagination reproduced the unpaged stable
  order across score, entity-type, equal case-folded title and UUID boundaries
  without gaps or duplicates.
- PASS: API regression coverage followed a real cursor and rejected checksum
  alteration plus reuse with a different query, entity type, source,
  intelligence type, lower date or upper date using stable 422 errors.
- PASS: generated OpenAPI exposes the bounded `cursor` query parameter and
  nullable `next_cursor` response field.
- PASS: complete PostgreSQL-backed suite, 90 tests with warnings fatal and no
  warning output.
- PASS: Ruff lint and formatting across 135 files; Pyright with zero errors and
  warnings; `git diff --check`.
- PASS: uv lock check resolved the unchanged 63-package lock.
- PASS: Alembic has one current head, `4c7d9e2a1b5f`, and reports no model drift;
  this task intentionally adds no migration.
- PASS: hosted CI run
  [#29](https://github.com/krutarth92/WatchTower/actions/runs/36898432274)
  passed Backend checks, Python dependency audit and Container build and scan
  on implementation commit `03782c9a0370155c1dff7ce7a3b7de8eb918ca63`.
- PASS: branch CI run
  [#30](https://github.com/krutarth92/WatchTower/actions/runs/36898668711)
  passed the same three jobs on evidence commit
  `48100f4c77cef5ca35415221444bee7fe227149c`.
- PASS: protected-main CI run
  [#31](https://github.com/krutarth92/WatchTower/actions/runs/36898912413)
  passed Backend checks, Python dependency audit and Container build and scan
  on `48100f4c77cef5ca35415221444bee7fe227149c`; the run retained its SBOM
  artifact.

## Human review checkpoint

Stop after local validation and the protected-branch run pass. Present the API
contract, no-gap/no-duplicate evidence and exact hosted run before beginning
another task.

## Transition verification

The user's next-task request on 2026-10-01 satisfied this checkpoint. Before
Task 25 began, local and remote `main` were clean and identical at
`7e3bdcd2448c19df2fc246cce9e89360de3859a7`. The search implementation and
relevant diff were reinspected. The focused PostgreSQL-backed search suite
passed all 6 tests; Ruff lint, Ruff formatting and `git diff --check` passed.
Protected-main CI run
[#33](https://github.com/krutarth92/WatchTower/actions/runs/36899269027)
passed Backend checks, Python dependency audit and Container build and scan on
that exact commit and retained its SBOM artifact.
