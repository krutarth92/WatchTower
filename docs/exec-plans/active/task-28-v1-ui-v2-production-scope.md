# Task 28: V1 UI and V2 productionization boundary

Status: scope update and local documentation validation complete; exact-commit
hosted CI pending.
Date: 2026-10-21.
Source: owner decision to complete the UI before any AWS deployment.

## Prior-task verification

Task 27 was verified before this scope task began. Local `main` and
`origin/main` matched clean commit
`3614f41f3279dd5e756f68c464e48fe83ca8025d`. The final implementation, tests,
CloudFormation template, deployment runbook, documentation diff and validation
record were inspected. `git diff --check HEAD^..HEAD` passed.

Branch CI
[#73](https://github.com/krutarth92/WatchTower/actions/runs/39491661831)
and protected-main CI
[#74](https://github.com/krutarth92/WatchTower/actions/runs/39491927104)
both passed backend checks, Python dependency audit and container
build/Trivy/SBOM for the final Task 27 state. Task 27 recorded 114 passing tests
and one explicitly environment-gated disposable-S3 integration skip; the skip
was not reported as passed. Jira `SCRUM-11` is Done, while the external AWS
approval, deployment and acceptance tickets remain open.

## Owner decision

The owner decided on 2026-10-21 that WATCHTOWER will not be deployed to AWS
immediately. V1 will instead finish with a usable first-party UI over the
completed backend for local/private operation. AWS deployment and operational
proof become a V2 productionization phase after UI acceptance.

This changes release sequencing, not the security standard. Existing AWS
templates and runbooks remain valid future inputs. WATCHTOWER must not claim
internet-facing production readiness until the V2 deployed evidence passes.

## Deliverables

- Amend the V1 scope to include a first-party SvelteKit/TypeScript UI and remove
  AWS deployment evidence from V1 acceptance.
- Add an explicit V2 productionization scope covering G03–G10 deployment and
  operational evidence.
- Update the readiness audit, README, setup and production-boundary status so
  the V1/V2 distinction is consistent.
- Keep live RAG and other optional product-policy decisions separately gated.
- Update Jira production epics as V2 work without closing their open evidence
  tickets, and create a V1 UI epic only after the repository scope is final.

## Acceptance criteria

- V1 clearly means the completed backend plus an accepted local/private UI.
- V2 clearly owns AWS identity/edge, durable data deployment, restore proof,
  staging/rollback, monitoring/capacity and immutable release publication.
- No document calls the existing templates deployed or claims production
  readiness.
- The next executable task is UI experience/API-contract planning, not AWS
  provisioning.
- Documentation links resolve, terminology is consistent and
  `git diff --check` passes.
- Hosted CI passes for the final documentation state.

## Validation record

- Inspected the amended V1 scope, new V2 productionization scope, readiness
  audit, README, setup guide and retained production-security contract for a
  consistent release boundary.
- Relative Markdown link validation: PASS for every changed document.
- Contradiction search found no remaining statement that frontend work is
  outside V1, V1 is backend-only, or AWS deployment proof is a V1 release gate.
- `git diff --check`: PASS.
- Application tests were not repeated locally because this task changes
  documentation and Jira sequencing only. Task 27's unchanged application and
  infrastructure state passed protected-main CI
  [#74](https://github.com/krutarth92/WatchTower/actions/runs/39491927104)
  immediately before this task. The hosted workflow will repeat all required
  backend, dependency and container checks for the final documentation commit.
- No AWS resource, Jira evidence ticket, application contract or runtime
  setting was deleted. No AWS resource, DNS record or public endpoint was
  created.
