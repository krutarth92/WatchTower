# Production security boundary

Status: Task 25 application and deployment contract, 2026-10-19.

This contract selects AWS Application Load Balancer (ALB), AWS Certificate
Manager (ACM), AWS WAF and Amazon Cognito for the first production boundary. It
does not provision AWS resources or authorize public release. DNS ownership,
certificate issuance, measured rate thresholds, an approved production VPC and
an operations owner remain deployment inputs.

## Request path and ownership

```text
internet client
  -> Route 53 or approved DNS
  -> ALB HTTPS listener using ACM certificate
  -> AWS WAF web ACL
  -> private EC2 target port allowed only from the ALB security group
  -> WATCHTOWER trusted-host/proxy middleware
  -> public route or Cognito bearer-token operator dependency
  -> PostgreSQL/Redis on private application networks
```

The ALB owns TLS negotiation, HTTP-to-HTTPS redirect, connection/header limits
and the forwarding-header boundary. WAF owns shared abuse controls across all
application processes. FastAPI owns token verification, roles, stable errors
and attributable operator actions. Application-local counters must not replace
the shared WAF rate policy.

## ALB, ACM and network controls

- Use a public ALB with an HTTPS 443 listener and an ACM-managed certificate for
  the approved API hostname. Port 80 may only redirect to HTTPS.
- Place API EC2 targets in private subnets without public IP addresses. The API
  target security group accepts its application port only from the ALB security
  group. PostgreSQL and Redis remain private and accept no ALB traffic.
- Enable invalid-header dropping and keep WAF fail-open disabled. Review ALB
  desync mitigation, idle timeout, request logging and retention with the
  operations owner.
- Keep ALB `X-Forwarded-For` processing in append mode. Treat the value as log
  context only; never use it as an authentication or authorization fact.
- Set `WATCHTOWER_TRUSTED_HOSTS` to the exact public API names. Set
  `WATCHTOWER_PROXY_TRUSTED_HOSTS` to the approved ALB source subnet CIDRs. The
  security-group restriction and application CIDR allowlist form one trust
  boundary. Wildcards are rejected in production.

The current private staging Compose file remains loopback-only and disables
proxy headers. A production target must publish the API port on the private EC2
interface so the ALB can reach it; it must not open that port to the internet.

## WAF policy

Attach one web ACL to the ALB. Start with AWS-managed common protections and
rate-based rules for public reads and stricter operator-route rules. Choose the
actual request and burst limits from representative staging traffic; this
document deliberately does not invent thresholds. Log sampled blocks without
request authorization headers or bodies, alert on sustained blocks and test the
rule action in count mode before enforcement where operationally appropriate.

## Cognito token and role contract

Create one Cognito user pool and app client for WATCHTOWER operators. Require
MFA, disable self-registration and define two groups:

- `operator`: protected ingestion, artifact, research, export and advisory
  authoring routes.
- `publisher`: includes operator capability and permits advisory publication.

Clients send an access token as `Authorization: Bearer <token>`. WATCHTOWER
accepts only RS256 tokens whose signature resolves through the fixed configured
JWKS URL and whose issuer, expiration, issued-at time, token use, client ID,
subject and token ID validate. It reads roles only from `cognito:groups`.
Keys are cached for a bounded interval and refreshed by key ID through PyJWT's
JWKS client. A JWKS connection outage returns a stable 503; invalid credentials
return 401 and insufficient roles return 403.

The immutable Cognito `sub` becomes authoritative advisory creation and
publication attribution. Caller-supplied author/publisher strings remain
accepted during the static-token migration but are ignored in OIDC mode. Logs
record the subject, display identity, roles, authentication method, token ID and
request ID without recording tokens or raw claims.

## Production settings

Provide these values through the approved secret/configuration service. The
values below are shapes, not usable credentials:

```dotenv
WATCHTOWER_ENVIRONMENT=production
WATCHTOWER_OPERATOR_AUTH_MODE=oidc
WATCHTOWER_OIDC_ISSUER=https://cognito-idp.ap-south-1.amazonaws.com/USER_POOL_ID
WATCHTOWER_OIDC_JWKS_URL=https://cognito-idp.ap-south-1.amazonaws.com/USER_POOL_ID/.well-known/jwks.json
WATCHTOWER_OIDC_CLIENT_ID=COGNITO_APP_CLIENT_ID
WATCHTOWER_OIDC_OPERATOR_GROUP=operator
WATCHTOWER_OIDC_PUBLISHER_GROUP=publisher
WATCHTOWER_TRUSTED_HOSTS=["api.example.com"]
WATCHTOWER_PROXY_TRUSTED_HOSTS=["10.0.1.0/24","10.0.2.0/24"]
```

Production startup rejects static authentication, an operator token, missing
OIDC values, wildcard/empty host policy and wildcard/empty proxy trust. Local
development and the existing private SSH-tunnel staging flow keep static mode
until Cognito staging is available.

## Rotation, revocation and rollback

Cognito owns password, MFA, account disablement, group membership and signing
key rotation. Remove a user from groups or disable the account to prevent new
access tokens, and set an access-token lifetime consistent with the incident
response target. Existing short-lived tokens remain valid until expiry unless a
separate revocation check is added, so the security owner must document that
window.

Roll back application code only to a version that understands the same OIDC
settings and role contract. Do not restore a shared static token in production
as a rollback. If Cognito or JWKS access fails, protected routes fail closed
while public reads can remain available; use the private incident channel for
recovery.

## Deployment acceptance evidence

Before public release, record evidence that:

1. the certificate and hostname validate and HTTP redirects to HTTPS;
2. direct EC2 application-port access is denied outside the ALB security group;
3. untrusted Host and forwarding headers are rejected or ignored;
4. missing, malformed, expired, wrong-issuer and wrong-client tokens return 401;
5. an operator cannot publish, while a publisher can;
6. Cognito `sub`, not request data, is persisted for publication attribution;
7. WAF rate rules apply across repeated requests and generate usable alerts;
8. ALB/WAF/application logs contain no tokens, cookies or request bodies; and
9. the previous compatible image can be restored without weakening OIDC.
