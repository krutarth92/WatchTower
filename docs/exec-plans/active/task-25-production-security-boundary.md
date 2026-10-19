# Task 25: production security boundary

Status: application boundary implemented and branch-verified; protected-main and deployment evidence pending.
Date: 2026-10-19.
Source: V1 readiness gaps G03 and G04.

## Prior-task verification

Task 24 was reinspected before this task began. Local and remote `main` matched
`7e3bdcd2448c19df2fc246cce9e89360de3859a7` with a clean tree. The search API,
schema, service, tests and documentation matched the approved cursor contract.
The focused PostgreSQL-backed search suite passed all 6 tests. Ruff lint, Ruff
formatting and `git diff --check` passed. Protected-main CI run
[#33](https://github.com/krutarth92/WatchTower/actions/runs/36899269027)
passed all three required jobs and retained its SBOM artifact. The user's
next-task request satisfied Task 24's human review checkpoint.

The first attempted local test command set the runtime database variable and
correctly skipped all 6 integration tests. A second attempt used a guessed
credential and failed to authenticate to the local database. Neither result was
counted as a pass. The recorded passing run loaded the existing ignored `.env`
configuration without printing it and set the required test database variable.

## Existing boundary

- Public reads and operator routes share the FastAPI service.
- Operator routes use one constant-time-compared static header token. It has no
  user identity, role, MFA, expiry, revocation or attributable audit subject.
- Private staging binds the API to EC2 loopback and is accessed through an SSH
  tunnel. Uvicorn deliberately ignores proxy headers.
- No production TLS endpoint, host allowlist, trusted forwarding boundary or
  shared rate limiter exists.
- Publication attribution is supplied in request data rather than derived from
  an authenticated principal.

## Recommended production choice

Use an AWS-managed boundary consistent with the approved Ubuntu EC2 direction:

1. Terminate HTTPS at an Application Load Balancer using an ACM certificate.
   Redirect HTTP to HTTPS and allow the EC2 application port only from the ALB
   security group. Keep PostgreSQL and Redis private.
2. Attach AWS WAF to the ALB for shared request-rate, body and common exploit
   controls. Keep application query/body limits as defense in depth.
3. Use an Amazon Cognito user pool as the OIDC issuer. Require MFA for operator
   accounts and short-lived access tokens.
4. Validate bearer access tokens in the application against the configured
   issuer, audience/client ID, algorithm and cached JWKS. Fail closed when the
   identity configuration is absent outside development and test.
5. Use explicit Cognito group claims for authorization. Start with `operator`
   for current protected reads/actions and `publisher` for publication actions.
   Do not accept caller-supplied author/publisher identity as authoritative.
6. Record the immutable token subject and approved display identity in audit
   fields and structured security events. Never log tokens or raw claims.
7. Accept forwarded scheme/client information only through the approved ALB
   path, configure an explicit public host allowlist, and do not use forwarded
   client IP as an authorization fact. WAF owns shared rate enforcement.
8. Retain the static operator token only for local development and private
   staging during migration; reject it in production after OIDC is enabled.

This choice keeps identity verification in the application, where every
operator route can enforce roles and supply an attributable principal. It also
keeps TLS and distributed abuse controls at the shared edge.

## Alternatives considered

| Option | Result |
| --- | --- |
| Generic OIDC issuer plus ALB/WAF | Technically sound and more portable, but no non-AWS identity owner has been selected. The configuration contract can remain standards-based even if Cognito is the first issuer. |
| ALB Cognito authentication action only | Useful for browser sessions, but the current product is an API and needs bearer-token role enforcement and an application principal for audit records. |
| Static token behind a TLS reverse proxy | Improves transport security but does not resolve identity, roles, MFA, expiry, revocation or attribution; it cannot close G03. |
| Process-local application rate limiting | Does not provide one shared limit across workers and would trust ambiguous client identity; it cannot close G04. |

## Approval record

The user approved continuing to Task 25 after reviewing the proposed boundary.
That approval selected the AWS ALB + ACM + WAF + Cognito application and
deployment contract. It did not authorize provisioning AWS resources or an
internet-facing release.

## Implemented application boundary

- Add a standards-based OIDC settings contract and token verifier with bounded
  JWKS caching, issuer/audience/algorithm checks, clock-skew bounds and stable
  401/403 errors.
- Replace the route dependency's `None` result with an immutable operator
  principal carrying subject, display identity and roles.
- Require `publisher` for advisory publication and derive publication identity
  from the principal. Preserve current request compatibility only where it does
  not allow forged attribution.
- Add configuration and regression tests for missing, expired, wrong-issuer,
  wrong-audience, malformed and insufficient-role tokens, plus log-redaction
  checks.
- Add explicit production trusted-host and proxy settings without weakening the
  private staging default.
- Document ALB, ACM, WAF, Cognito, security-group, token-rotation/revocation and
  rollback requirements. Do not provision AWS resources or store secrets.

The implementation uses Cognito-compatible RS256 access tokens, exact issuer,
client ID and token-use checks, a bounded PyJWT JWKS cache, explicit
`operator`/`publisher` roles and an immutable authenticated principal. Advisory
creation and publication derive attribution from the OIDC subject. Local and
private staging retain the constant-time static token path, while production
configuration rejects static authentication, wildcard/missing host allowlists
and wildcard/missing proxy trust.

`docs/security/production-boundary.md` assigns TLS to ALB/ACM, shared abuse
controls to WAF, identity and MFA to Cognito, and token/role enforcement to the
application. No AWS resources were provisioned.

## Acceptance criteria

- Every protected route has an authenticated subject and explicit role policy.
- Publication attribution cannot be forged through request data.
- Production fails closed when OIDC, host or proxy trust configuration is
  incomplete.
- Tokens and sensitive claims remain absent from logs and stable error bodies.
- TLS, shared rate limiting and forwarding trust have one documented AWS edge
  owner and testable deployment contract.
- Static-token behavior remains available only for local/private migration and
  is rejected in production.
- The full warning-free suite, Ruff, formatting, Pyright, Alembic, dependency
  audit, container scan and protected-main checks pass.

## Approval checkpoint

Satisfied before implementation by the user's instruction to continue to the
next task. Task 25 remains at its post-implementation review checkpoint until
the branch and protected-main checks pass.

## Validation record

| Check | Result |
| --- | --- |
| Focused authentication and foundation tests | PASS: 22 tests |
| PostgreSQL-backed advisory tests | PASS: 3 tests |
| Full PostgreSQL-backed suite with warnings fatal | PASS: 102 tests |
| Ruff lint | PASS |
| Ruff formatting | PASS: 138 files formatted |
| Pyright | PASS: 0 errors, 0 warnings |
| `uv lock --check` | PASS: 67 packages resolved |
| Runtime and development requirements export | PASS: regenerated from `uv.lock` |
| Alembic heads/current/check | PASS: sole/current head `4c7d9e2a1b5f`; no drift |
| OpenAPI security contract | PASS: bearer and static-header alternatives declared |
| Local Docker build and installed-package smoke import | PASS: `watchtower:task25`, PyJWT 2.15.1 |
| Branch CI #50 | PASS: backend, dependency audit, container build/Trivy scan, SBOM evidence |
| `git diff --check` | PASS |

The complete suite initially found one test-isolation defect: earlier logging
configuration routed the audit event through its installed JSON handler instead
of pytest's inherited capture handler. The test now attaches pytest's handler
directly, and the final full run passed.

Hosted branch run
[#49](https://github.com/krutarth92/WatchTower/actions/runs/39196875274)
passed the backend and Python dependency-audit jobs but failed the container
scan. Trivy found patched Debian updates available for the base image's
`libpcre2-8-0` and `perl-base` packages. The Dockerfile now refreshes package
metadata, installs available base-image security updates noninteractively and
removes the apt lists before application installation. A local rebuild confirms
`libpcre2-8-0` `10.42-1+deb12u2`, `perl-base` `5.36.0-7+deb12u4`, OpenSSL
`3.0.22-1~deb12u1`, and a successful application/PyJWT smoke import. The
successor hosted run
[#50](https://github.com/krutarth92/WatchTower/actions/runs/39197256407)
passed the backend, Python dependency-audit and container build/Trivy scan jobs.
It retained the unexpired commit-specific
`watchtower-sbom-c5e5d028baa88743399d5d3c613bed170170ffaf` artifact.

AWS acceptance evidence remains a deployment prerequisite and is not reported
as complete.
