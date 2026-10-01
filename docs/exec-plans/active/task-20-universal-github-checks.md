# Task 20: universal GitHub checks

Status: complete, verified and approved.
Date: 2026-10-01.
Source: user request to run fair, consistent checks whenever code is pushed to
GitHub.

## Prior-task verification

Task 19 was reinspected before this task began. Local `main` and `origin/main`
matched commit `65b6466`, the working tree was clean, and GitHub Actions run
[#10](https://github.com/krutarth92/WatchTower/actions/runs/36821809824)
passed Backend checks, Python dependency audit and Container build and scan.
The final workflow had no configuration warning; GitHub emitted only scheduled
runner-image migration notices. The user's next-task request satisfied Task 19's
human review checkpoint.

## Goal and policy

Apply the same repository-owned CI checks to every branch push and every pull
request. Keep manual dispatch for diagnosis. Require the three stable CI job
results before changes can merge into `main` when GitHub repository settings
support required status checks.

The policy is deliberately branch- and author-neutral: contributor, Dependabot
and maintainer changes receive the same checks. Concurrency may cancel an older
run only when a newer commit arrives on the same ref.

## Scope

1. Remove the `main`-only filter from the workflow's `push` event.
2. Preserve pull-request and manual triggers.
3. Keep Backend checks, Python dependency audit and Container build and scan as
   the required check set; do not add arbitrary or duplicate gates.
4. Validate the workflow locally and obtain a green hosted run for the exact
   commit.
5. Configure `main` to require those successful checks before merge if GitHub
   exposes the setting for this repository.

This task does not merge dependency updates, change application behavior,
deploy infrastructure or weaken a failing security/dependency result.

## Acceptance criteria

- A push to any branch matches the CI workflow trigger.
- Pull requests and manual dispatch remain enabled.
- All three jobs pass on the exact published commit.
- The GitHub enforcement result is recorded accurately; an unavailable setting
  is reported as blocked rather than passed.
- Local and remote `main` match and the working tree is clean.

## Validation record

- Parsed `.github/workflows/ci.yml` locally and confirmed `push`,
  `pull_request` and `workflow_dispatch` are enabled without a branch filter.
  `git diff --check` passed.
- Commit `151d0de` (`ci: run checks on every branch push`) was pushed normally.
  Hosted CI run
  [#11](https://github.com/krutarth92/WatchTower/actions/runs/36822064571)
  passed Backend checks in 43 seconds, Python dependency audit in 21 seconds,
  and Container build and scan in 39 seconds.
- Active ruleset
  [Require WATCHTOWER CI on main](https://github.com/krutarth92/WatchTower/settings/rules/24292023)
  targets the default branch and requires those three GitHub Actions checks.
  It has no bypass actor, does not require stale-branch updates, and adds no
  reviewer, signature, linear-history, deletion or force-push rule.
- Commit `f9f15b3` was pushed first to `codex/task-20-github-checks`. Hosted CI
  run
  [#12](https://github.com/krutarth92/WatchTower/actions/runs/36850297262)
  passed Backend checks in 46 seconds, Python dependency audit in 26 seconds,
  and Container build and scan in 45 seconds. The identical checked commit then
  fast-forwarded successfully to protected `main`, proving that the ruleset
  accepts a commit only after the configured checks report success.

## Acceptance record

- Every-branch push, pull-request and manual triggers: **pass**.
- Same checks for maintainers, contributors and dependency automation: **pass**.
- Exact published commit passed all three hosted jobs: **pass**.
- Active default-branch rule requires exactly those three jobs: **pass**.
- Checked-branch commit accepted by protected `main`: **pass**.
- No application behavior, dependency or deployment change: **pass**.

## Human review checkpoint

The user requested the next task and authorized continuation. Task 20 was then
completed and verified through the protected-branch flow above. Begin the next
remediation only after reinspecting this record and the matching remote state.
