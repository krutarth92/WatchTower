# Production edge deployment and acceptance

Status: validation-only runbook. Creating or changing AWS resources, DNS, or a
public endpoint requires a separately approved deployment change.

This runbook deploys the repository contract in
`infra/aws/production-edge.template.json`. It creates the Cognito operator
directory, ALB listeners and target group, WAF policy, security-group boundary,
and retained access logs. It consumes an existing VPC, public subnets, private
API instance and security group, ACM certificate, and approved hostname.

## Ownership and required inputs

Record one named owner for identity lifecycle, network/DNS, security monitoring,
and application release before creating a change set. The reviewer must confirm:

- the API instance has no public IP and is reachable from every selected ALB
  subnet on the application port;
- its existing security group has no internet or broad VPC ingress on that port;
- the public subnets have the intended route to an internet gateway and span at
  least two Availability Zones;
- the ACM certificate is issued in the deployment Region and covers the exact
  API hostname;
- the DNS owner can create an alias to the ALB after acceptance;
- `PublicRateLimit` and `OperatorRateLimit` come from representative staging
  traffic and an approved abuse budget. The template intentionally has no rate
  defaults;
- the chosen access-log retention periods meet the organization's policy; and
- CloudWatch/WAF metrics have an alert receiver and incident owner.

The template does not create Route 53 records or a certificate. This prevents a
repository deployment from claiming a hostname it does not own.

## Validate and review a change set

Use a reviewed parameter file outside the repository. Do not store account IDs,
instance IDs, certificate ARNs, email addresses, or operator credentials here.

```powershell
aws cloudformation validate-template `
  --template-body file://infra/aws/production-edge.template.json

aws cloudformation create-change-set `
  --stack-name watchtower-production-edge `
  --change-set-name REVIEW_IDENTITY_AND_EDGE `
  --change-set-type CREATE `
  --template-body file://infra/aws/production-edge.template.json `
  --parameters file://PATH_TO_REVIEWED_PARAMETERS.json

aws cloudformation describe-change-set `
  --stack-name watchtower-production-edge `
  --change-set-name REVIEW_IDENTITY_AND_EDGE
```

Creating the change set does not deploy it. Review all resources, replacements,
retention behavior, rate values, target identity, and security-group changes.
Execution requires the deployment approval recorded for that environment.

## Identity setup

After an approved stack deployment:

1. Create operators through the administrative Cognito workflow. Self-sign-up
   remains disabled.
2. Require the initial password change and software-token MFA enrollment before
   granting either group.
3. Add every protected-route user to `operator`. Add approved publishers to
   both `operator` and `publisher`; Cognito groups do not inherit membership.
4. Record joiner, group-change, disablement, and periodic access-review events in
   the organization's identity audit system.
5. On departure or suspected compromise, disable the user, revoke refresh
   tokens, and remove group membership. Access tokens are deliberately short
   lived, but can remain valid until expiry.

Use the stack outputs to configure the application:

```dotenv
WATCHTOWER_ENVIRONMENT=production
WATCHTOWER_OPERATOR_AUTH_MODE=oidc
WATCHTOWER_OIDC_ISSUER=COGNITO_ISSUER_OUTPUT
WATCHTOWER_OIDC_JWKS_URL=COGNITO_JWKS_URL_OUTPUT
WATCHTOWER_OIDC_CLIENT_ID=COGNITO_CLIENT_ID_OUTPUT
WATCHTOWER_OIDC_OPERATOR_GROUP=operator
WATCHTOWER_OIDC_PUBLISHER_GROUP=publisher
WATCHTOWER_TRUSTED_HOSTS=["APPROVED_API_HOSTNAME"]
WATCHTOWER_PROXY_TRUSTED_HOSTS=["APPROVED_ALB_SUBNET_CIDR_1","APPROVED_ALB_SUBNET_CIDR_2"]
```

Keep these values in the approved configuration service. Cognito credentials and
tokens never belong in `.env` on a production host or in Git.

## Network and application acceptance

Run acceptance from an external client, the private host, and an authorized
operator client. Save command output with tokens redacted.

1. Create the DNS alias to the stack's `AlbDnsName`, then verify certificate
   hostname/chain validation and that HTTP returns only a redirect to HTTPS.
2. Verify the private instance/application port cannot be reached from the
   internet or any source outside the ALB security group.
3. Confirm `/health` and `/ready` return 200 through the approved hostname and
   that an unapproved `Host` value is rejected.
4. Send forged `X-Forwarded-For` and forwarding host/protocol values. Confirm the
   ALB appends its forwarding context and the application trusts only traffic
   arriving from the approved ALB subnet CIDRs.
5. Confirm protected routes return 401 for absent, malformed, expired,
   wrong-issuer, wrong-client and ID tokens. Use Cognito access tokens only.
6. Confirm an `operator` can use protected non-publication routes but receives
   403 for publication. Confirm a dual-group publisher can publish and that the
   persisted attribution equals the immutable Cognito `sub`.
7. Exercise the WAF rules in count mode first if the reviewer requires it, then
   restore the reviewed blocking action. Confirm public and operator paths use
   their separate measured limits across repeated clients and instances.
8. Inspect WAF, ALB and application logs. Confirm WAF retains only counted or
   blocked requests, authorization and cookie fields are redacted, and tokens,
   raw claims and request bodies are absent. Confirm retained ALB objects are
   private and CloudWatch retention matches the stack.
9. Confirm WAF metrics and an intentional alarm test reach the assigned owner.

Do not call the boundary production-ready until all nine results are attached to
the deployment record with stack ID, template commit, Region, hostname, test
time, reviewer, and unresolved findings.

## Rollback

Application rollback may use only a previously verified image that supports the
same OIDC, trusted-host and proxy settings. Never restore static-token mode in
production. If Cognito or JWKS is unavailable, protected routes fail closed;
public reads may remain available while the identity owner restores service.

For an edge regression, remove DNS traffic from the affected ALB or restore the
last reviewed stack/template parameters through another approved change set.
Retained Cognito and log resources are deliberate. Do not delete the stack to
work around a fault, and do not disable ALB deletion protection or Cognito
deletion protection without a separate destructive-change review.

## Evidence record

Record these fields after each deployment or rehearsal:

- stack ID, change-set ID, template commit, account alias and Region;
- certificate ARN suffix and approved hostname;
- target instance/private-subnet evidence and effective security-group rules;
- selected public/operator limits and the staging measurement that justified
  them;
- Cognito pool/client IDs, token lifetime, MFA and group-review evidence;
- acceptance results 1–9, relevant log/metric links and alert receiver;
- rollback result and elapsed time; and
- operator, security reviewer, date and remaining issues.
