# Task 23: warning-free TestClient migration

Status: complete; review checkpoint active.
Date: 2026-10-01.
Source: remaining V1 readiness gap G15.

## Prior-task verification

Task 22 was reinspected before this task began. Local `main` and `origin/main`
matched `63b3e7490c8945bee7f6d173ff9b1bb4822a1103` with a clean tree. The final
workflow retained the required job names, generated and validated CycloneDX
from the exact commit image, and uploaded only the SBOM, its checksum and image
ID for 30 days. Main CI run
[#21](https://github.com/krutarth92/WatchTower/actions/runs/36873669533)
passed all three required jobs on that commit and exposed the expected artifact.
The user's next-task request satisfied Task 22's review checkpoint.

## Goal and boundary

Move Starlette's test client onto its supported `httpx2` implementation while
retaining `httpx` for WATCHTOWER's production connector and worker code. Make
all pytest warnings fatal so a future fallback or new warning fails local and
hosted validation.

This is test-tooling maintenance. It must not change API behavior, production
HTTP client imports, database schema or deployment behavior.

## Acceptance criteria

- `httpx2` is a development dependency with an explicit compatible range and
  is represented in the lockfile and development requirements export.
- Production `httpx` remains a runtime dependency for connector and worker use.
- Starlette `TestClient` selects `httpx2`; the legacy fallback warning is gone.
- Pytest treats warnings as errors and the complete PostgreSQL-backed suite
  passes with zero warnings.
- Lock/export checks, Ruff, formatting, Pyright and Alembic validation pass.
- The exact commit passes the three protected-branch GitHub checks.

## Validation record

- PASS: `httpx2==2.13.1` is locked only in the development group and the
  generated development export; the production export is unchanged.
- PASS: a runtime probe reported `TestClient` inherits from `httpx2.Client`,
  while WATCHTOWER's runtime `httpx` remains at 0.28.1.
- PASS: the complete PostgreSQL-backed suite passed all 88 tests with pytest's
  global warnings-as-errors policy active and emitted no warnings.
- PASS: Ruff lint and formatting checks passed across 134 files.
- PASS: Pyright passed with zero errors and warnings after the advisory fixture
  received a precise typed shape compatible with the new client annotations.
- PASS: Alembic has one current head, `4c7d9e2a1b5f`, and reports no model drift.
- PASS: uv resolved 63 locked packages; frozen production and development
  exports regenerated reproducibly.
- PASS: hosted CI run
  [#22](https://github.com/krutarth92/WatchTower/actions/runs/36875847023)
  passed Backend checks, Python dependency audit and Container build and scan
  on implementation commit `6459f863c130fd9cb147596987eddda7b5992dd0`.

## Human review checkpoint

Stop after local validation and the protected-branch run pass. Present the
dependency boundary, warning enforcement and exact hosted run before beginning
another task.
