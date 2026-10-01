# Task 21: canonical publication visibility

Status: complete, verified and approved; Task 22 started.
Date: 2026-10-01.
Source: V1 readiness gap G02.

## Prior-task verification

Task 20 was reinspected before this task began. Local and remote `main` matched
commit `01b86a6`, the working tree was clean, the active GitHub ruleset targeted
`main` with the three intended checks and no bypass, and hosted run
[#15](https://github.com/krutarth92/WatchTower/actions/runs/36850720610)
passed Backend checks, Python dependency audit and Container build and scan.
The user's request to continue satisfied Task 20's review checkpoint.

## Approved policy

The project owner accepted the recommended explicit per-record policy on
2026-10-01. `Source`, `Actor`, `Alias`, `Observation`, `Evidence`, `Behavior`,
`Technique` and `Campaign` each have an `internal` or `published` state. Both
the ORM and database default to `internal`, including migrated rows. Ingestion
cannot publish records implicitly.

Public actor routes require a published Actor and return only published linked
records whose required Source is also published. An internal Actor uses the
same 404 response as an absent UUID. Actor name/alias search and every
cross-entity search branch apply the same visibility boundary.

Publication state is an internal gate and is not added to public response
schemas. This task does not add a publication write endpoint, infer an editor
identity, publish existing data automatically or expose raw evidence/artifacts.
An authenticated, attributable editorial workflow remains a later bounded task.

## Deliverables

- Shared fail-closed model state on all records exposed by actor/search reads.
- Alembic revision `4c7d9e2a1b5f` with indexed state columns and downgrade.
- Actor detail, alias, observation, timeline, association and reference filters.
- Actor lookup and cross-entity search filters across every entity branch.
- Regression coverage for internal actor non-disclosure, nested-record omission,
  default state and internal cross-entity search exclusion.
- Updated public API, search and threat-model contracts.

## Validation record

- PASS: focused actor/search integration suite, 15 tests.
- PASS: Ruff and Pyright after implementation.
- PASS: Alembic upgraded from `0218f83cad8e` to `4c7d9e2a1b5f`; one head.
- PASS: `alembic check` reports no new upgrade operations.
- PASS: migration downgrade to `0218f83cad8e` and upgrade back to head.
- PASS: full suite, 88 tests; one known TestClient/httpx deprecation warning.
- PASS: repository Ruff, formatting and Pyright checks.
- PASS: hosted CI run
  [#16](https://github.com/krutarth92/WatchTower/actions/runs/36859340017)
  on implementation commit `6b8c240`: Backend checks, Python dependency audit
  and Container build and scan all completed successfully.

## Human review checkpoint

Stop after all validation and hosted CI pass. Present the selected contract,
privacy behavior, migration impact and remaining editorial-workflow dependency
for review before starting another readiness task.

The user requested the next task after reviewing the completion report. Before
Task 22 began, the clean `main` state, migration head/drift, Ruff result, focused
privacy suite and successful protected-main run #18 were reverified.
