# Task 27: production identity and edge infrastructure

Status: repository implementation and validation complete. AWS provisioning and
public release are not authorized by this task.
Date: 2026-10-21.
Source: V1 readiness gaps G03 and G04.

## Prior-task verification

Task 26 was inspected and revalidated before this task began. The final files,
diff, lock/export update, validation record and exact commit were checked rather
than relying on the earlier completion message. Local `main` and `origin/main`
match `3c0fe0d5c09cbf9ac800123ae9cc4893cfa9504a` with a clean worktree.

The first corrected pre-merge run
[#63](https://github.com/krutarth92/WatchTower/actions/runs/39488455411)
failed dependency audit after advisory `GHSA-6q48-6c7w-9gw2` was published for
the locked certifi version. That run is recorded as failed. Task 26 updated only
certifi to fixed `2026.10.19`, reran local validation, and passed branch run
[#64](https://github.com/krutarth92/WatchTower/actions/runs/39489020478) and
protected-main run
[#65](https://github.com/krutarth92/WatchTower/actions/runs/39489315546)
for the exact final commit. Each run passed backend, dependency-audit and
container/Trivy/SBOM jobs. Local validation passed Ruff, formatting, Pyright,
uv lock, Alembic and 110 PostgreSQL tests; the one external disposable-S3 test
remained skipped because no external resource was authorized and was not called
passed.

Jira readback records `SCRUM-2` through `SCRUM-8` as Done. `SCRUM-9`, the real
restore rehearsal, remains To Do, and the epic remains In Progress. This is
consistent with the Task 26 boundary: repository implementation is complete;
AWS deployment and measured recovery proof remain open.

## Goal and scope

Implement the approved Task 25 Cognito, ALB, ACM and WAF contract as a
reviewable CloudFormation template and an executable deployment/acceptance
runbook. The repository must encode identity, TLS, target isolation, header,
rate-limit and sanitized-log controls without inventing account-specific values.

This task does not create or modify AWS resources, DNS, certificates, users or
public endpoints. It does not authorize billable infrastructure or a production
release. Deployment requires a separate reviewed change with named owners and
measured rate thresholds.

## Deliverables

- `infra/aws/production-edge.template.json` with admin-only Cognito users,
  mandatory MFA, short-lived access tokens, explicit operator/publisher groups,
  retained identity/log resources, HTTPS ALB, HTTP redirect, private-target
  security-group ingress, managed WAF rules and separate measured public and
  operator rate policies.
- Private ALB access logs and WAF logs with bounded retention, no sampled
  request bodies, and redaction of authorization and cookie headers.
- Deterministic repository tests for the security contract.
- `docs/operations/production-edge-deployment.md` covering ownership,
  change-set review, identity lifecycle, acceptance evidence and fail-closed
  rollback.
- Security/readiness/setup documentation that distinguishes repository
  completion from external deployment evidence.

## Acceptance criteria

- The template parses and passes `cfn-lint` without provisioning anything.
- Cognito disables self-registration, requires software-token MFA, protects the
  pool from deletion and emits issuer/JWKS/client values used by WATCHTOWER.
- The ALB accepts public traffic only on 80/443, redirects HTTP, uses the
  provided certificate and modern TLS policy, logs access, rejects malformed
  headers, preserves Host, appends XFF, and reaches the API only through a
  security-group reference.
- WAF attaches to the ALB, uses AWS managed common/known-bad-input rules, has
  separate no-default rate parameters for public and operator paths, and
  redacts authorization/cookie headers from logs.
- The runbook requires proof of private targets, exact hostname/certificate,
  token failures, role separation, immutable subject attribution, shared rate
  behavior, log sanitation, alerts and compatible rollback.
- Ruff, formatting, Pyright, focused tests, complete PostgreSQL tests, uv lock,
  dependency audit, `git diff --check` and hosted CI pass for the final state.
- Any unavailable external deployment check is recorded as pending rather than
  passed.

## Approval boundary

The owner directed work to continue to the next task on 2026-10-21. That
authorizes this reversible repository implementation under the already approved
Task 25 architecture. No AWS deployment, DNS change, user creation or public
release is performed.

## Validation record

- `cfn-lint infra/aws/production-edge.template.json`: PASS. Its first run found
  an invalid empty WAF logging-filter list (`E3032`). The filter was replaced by
  a valid policy that drops ordinary allowed-request logs and retains counted or
  blocked requests. The failed run is not counted as acceptance evidence.
- Template contract tests: **4 passed** with cache disabled. A focused test run
  completed all assertions but then Windows denied access to the ignored pytest
  cache and warnings are fatal; the successful rerun used
  `-p no:cacheprovider`. The cache-error run is not counted as passed.
- Ruff and formatting: PASS; 151 files formatted. Pyright: PASS with 0 errors
  and 0 warnings.
- Docker PostgreSQL/Redis services: healthy. Alembic `heads` and `current`:
  `4c7d9e2a1b5f (head)`; `alembic check`: no new upgrade operations.
- Complete PostgreSQL-backed suite: **114 passed, 1 skipped**. The skip is the
  existing environment-gated disposable-S3 integration; no endpoint or bucket
  was authorized, so it is not reported as passed. The first suite attempt was
  blocked because the local virtual environment no longer had the project
  installed and Windows denied an existing native module. `uv sync --locked`
  restored the project environment before the successful rerun; the failed
  environment attempt is not acceptance evidence.
- `uv lock --check`: PASS with 73 packages. Source and wheel builds: PASS.
- Fully pinned runtime dependency audit: no known vulnerabilities; the two
  documented DiskCache exceptions were ignored.
- `docker build --tag watchtower:task27 .`: PASS. Image smoke test imported
  `watchtower` and `create_app` successfully.
- `git diff --check`: PASS. No AWS resource, user, DNS record, certificate or
  public endpoint was created or changed.
- Branch CI
  [#72](https://github.com/krutarth92/WatchTower/actions/runs/39491354312)
  passed backend checks, Python dependency audit and container
  build/Trivy/SBOM for exact implementation commit
  `5e8a16749626842d77d6f678b3a4816e40385d6e`.
