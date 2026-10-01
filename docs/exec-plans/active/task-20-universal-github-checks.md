# Task 20: universal GitHub checks

Status: active.
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

## Human review checkpoint

Stop after the workflow and supported GitHub enforcement are configured and
verified. Present the trigger, required checks, hosted run and any repository
plan limitation before beginning another task.
