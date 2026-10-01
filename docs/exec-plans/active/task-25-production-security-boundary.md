# Task 25: production security boundary

Status: architecture decision prepared; implementation requires human approval.
Date: 2026-10-01.
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

## Proposed implementation boundary after approval

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

Approve or replace the recommended AWS ALB + ACM + WAF + Cognito boundary before
implementation. Approval is required because this selects production identity
and ingress architecture and changes the operator authentication/API contract.
