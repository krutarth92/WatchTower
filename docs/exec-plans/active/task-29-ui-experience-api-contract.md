# Task 29: V1 UI experience and API contract

Status: implementation contract and validation complete; owner review pending.
Date: 2026-10-21.
Tracking: Jira `SCRUM-17`, parent epic `SCRUM-16`.

## Prior-task verification

Task 28 was verified before this task began. Local `main` and `origin/main`
matched clean commit `a0624994c5ac04e5215e6569334bad0e13eac12a`.
The final Task 28 scope commit, execution plan, V1 scope, V2 productionization
scope, readiness audit, README, setup guide and production-boundary document
were inspected. `git diff --check HEAD^..HEAD` passed.

Protected-main CI
[#77](https://github.com/krutarth92/WatchTower/actions/runs/39494948724)
passed on that exact commit. Backend checks, Python dependency audit and
container build/Trivy/SBOM all completed successfully, and the workflow retained
the commit-bound SBOM artifact. No Task 28 issue remains, so Task 29 may proceed.

## Goal

Define a concrete, reviewable V1 user experience and API boundary before adding
the frontend tree. The contract must let implementation work split into small
tasks without reopening product, visibility, authentication or error-state
decisions.

## Deliverables

- Identify the user, core research journey and information architecture.
- Define desktop/mobile behavior for search, actor context/timeline,
  evidence/provenance and published advisories.
- Map every screen to current public `/api/v1` responses and constraints.
- Specify loading, empty, partial, unavailable and stable API-error states.
- Decide the V1 browser operator/authentication boundary.
- Specify accessibility, visual language and ECharts use rules.
- Select a compatible frontend baseline, directory, checks and CI contract.
- Split the accepted design into executable implementation tasks.

## Decisions

- V1 is a read-only researcher interface over published public endpoints.
- Browser-based operator actions and token entry are excluded. This prevents a
  local static secret from becoming browser state and avoids implying an
  unapproved editorial workflow.
- The SvelteKit server owns the backend origin and API calls. Browser code uses
  same-origin UI routes and cannot choose an arbitrary upstream.
- Search results without an actor context remain self-contained cards because
  the backend has no public detail route for those entity types.
- ECharts is not installed until a complete series is available; a cursor page
  must not be presented as a complete chart.
- The UI renders API content as text and inherits fail-closed publication
  behavior from public endpoints.

## Files

- `docs/design/v1-ui-experience.md`
- `docs/exec-plans/active/task-29-ui-experience-api-contract.md`
- `docs/exec-plans/active/v1-readiness.md`

## Acceptance criteria

- The contract is concrete enough to implement without inventing screens,
  routes, states or security behavior.
- Public visibility remains consistent with the backend contract.
- `OBSERVED` and `ASSESSED` remain explicit in all typed UI content.
- Desktop, mobile, accessibility and failure behavior are specified.
- Package/version, test and CI choices are recorded.
- Relative links and terminology are valid, and `git diff --check` passes.
- Application tests may be marked not applicable because this task changes
  documentation only; final hosted CI must still validate the repository.
- The owner reviews this contract before frontend implementation begins.

## Validation record

- Inspected the implemented actor, search, advisory, error, publication and
  authentication contracts rather than relying on older design summaries.
- Verified every screen uses an existing public read route and does not expose
  operator-only resources, drafts or internal records.
- Checked the selected package metadata on the npm registry on 2026-10-21.
  SvelteKit 3.1.0 requires Svelte `^5.57.1`, Vite `^8.0.12` and TypeScript
  `^6.0.0`; the selected Svelte 5.57.2, Vite 8.3.4 and TypeScript 6.0.3 satisfy
  those peer ranges. The implementation task must still lock and build the
  complete dependency set together.
- Relative Markdown link validation: PASS for all three affected documents.
- Required language check: PASS for explicit `OBSERVED`/`ASSESSED`, operator
  token exclusion, private API origin, ECharts constraint, owner review and
  Task 30 handoff.
- Initial text-token contrast against its stated surface: PASS. Ratios range
  from 6.19:1 to 15.14:1, above the 4.5:1 normal-text target.
- `git diff --check`: PASS.
- Application tests are not applicable to this documentation-only task. No
  application, dependency, migration, workflow or runtime file changed. Final
  hosted CI must still repeat the repository's required checks on the exact
  published commit.
- No frontend dependency, runtime code, AWS resource or browser credential flow
  was created.
- Branch CI
  [#78](https://github.com/krutarth92/WatchTower/actions/runs/39496955103)
  passed backend checks, Python dependency audit and container
  build/Trivy/SBOM for exact contract commit
  `c1ffc886bd6f82df060a60b6a31f4b98d310f390`.

## Review checkpoint

Owner approval is required before starting Task 30. Until then, no frontend
dependencies or runtime code are added.

