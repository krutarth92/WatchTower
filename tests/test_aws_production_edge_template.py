import json
from pathlib import Path
from typing import Any


def _template() -> dict[str, Any]:
    path = Path("infra/aws/production-edge.template.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_production_identity_is_admin_managed_mfa_protected_and_short_lived() -> None:
    template = _template()
    parameters = template["Parameters"]
    resources = template["Resources"]

    pool = resources["OperatorUserPool"]
    properties = pool["Properties"]
    assert properties["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is True
    assert properties["DeletionProtection"] == "ACTIVE"
    assert properties["MfaConfiguration"] == "ON"
    assert properties["EnabledMfas"] == ["SOFTWARE_TOKEN_MFA"]
    assert properties["Policies"]["PasswordPolicy"]["MinimumLength"] >= 14
    assert pool["DeletionPolicy"] == "Retain"

    client = resources["OperatorUserPoolClient"]["Properties"]
    assert client["GenerateSecret"] is False
    assert client["EnableTokenRevocation"] is True
    assert client["PreventUserExistenceErrors"] == "ENABLED"
    assert client["AccessTokenValidity"] == {"Ref": "AccessTokenMinutes"}
    assert parameters["AccessTokenMinutes"]["MaxValue"] <= 60
    assert client["TokenValidityUnits"]["AccessToken"] == "minutes"

    groups = {
        resources["OperatorGroup"]["Properties"]["GroupName"],
        resources["PublisherGroup"]["Properties"]["GroupName"],
    }
    assert groups == {"operator", "publisher"}


def test_alb_enforces_https_private_target_boundary_and_sanitized_logging() -> None:
    template = _template()
    resources = template["Resources"]

    alb = resources["ApiLoadBalancer"]["Properties"]
    assert alb["Scheme"] == "internet-facing"
    attributes = {item["Key"]: item["Value"] for item in alb["LoadBalancerAttributes"]}
    assert attributes["deletion_protection.enabled"] == "true"
    assert attributes["access_logs.s3.enabled"] == "true"
    assert attributes["routing.http.drop_invalid_header_fields.enabled"] == "true"
    assert attributes["routing.http.desync_mitigation_mode"] == "strictest"
    assert attributes["routing.http.xff_header_processing.mode"] == "append"
    assert attributes["routing.http.preserve_host_header.enabled"] == "true"

    http = resources["HttpListener"]["Properties"]
    redirect = http["DefaultActions"][0]["RedirectConfig"]
    assert (http["Protocol"], http["Port"]) == ("HTTP", 80)
    assert redirect == {"Port": "443", "Protocol": "HTTPS", "StatusCode": "HTTP_301"}

    https = resources["HttpsListener"]["Properties"]
    assert (https["Protocol"], https["Port"]) == ("HTTPS", 443)
    assert https["Certificates"] == [{"CertificateArn": {"Ref": "CertificateArn"}}]
    assert https["SslPolicy"].startswith("ELBSecurityPolicy-TLS13-")

    ingress = resources["ApplicationIngressFromAlb"]["Properties"]
    assert ingress["GroupId"] == {"Ref": "ApplicationSecurityGroupId"}
    assert ingress["SourceSecurityGroupId"] == {"Ref": "AlbSecurityGroup"}
    assert "CidrIp" not in ingress and "CidrIpv6" not in ingress

    target = resources["ApiTargetGroup"]["Properties"]
    assert target["HealthCheckPath"] == "/ready"
    assert target["TargetType"] == "instance"
    assert target["Matcher"] == {"HttpCode": "200"}

    bucket = resources["AlbAccessLogBucket"]
    assert all(bucket["Properties"]["PublicAccessBlockConfiguration"].values())
    assert bucket["DeletionPolicy"] == "Retain"
    policy = resources["AlbAccessLogBucketPolicy"]["Properties"]["PolicyDocument"]["Statement"]
    statements = {statement["Sid"]: statement for statement in policy}
    assert statements["AllowAlbLogDelivery"]["Principal"] == {
        "Service": "logdelivery.elasticloadbalancing.amazonaws.com"
    }
    assert "aws:SourceArn" in statements["AllowAlbLogDelivery"]["Condition"]["ArnLike"]
    assert statements["DenyInsecureTransport"]["Effect"] == "Deny"


def test_waf_uses_managed_rules_separate_measured_limits_and_redacted_logs() -> None:
    template = _template()
    parameters = template["Parameters"]
    resources = template["Resources"]

    assert "Default" not in parameters["PublicRateLimit"]
    assert "Default" not in parameters["OperatorRateLimit"]

    web_acl = resources["ApiWebAcl"]["Properties"]
    assert web_acl["Scope"] == "REGIONAL"
    rules = {rule["Name"]: rule for rule in web_acl["Rules"]}
    assert rules["AwsManagedCommon"]["Statement"]["ManagedRuleGroupStatement"]["Name"] == (
        "AWSManagedRulesCommonRuleSet"
    )
    assert (
        rules["AwsManagedKnownBadInputs"]["Statement"]["ManagedRuleGroupStatement"]["Name"]
        == "AWSManagedRulesKnownBadInputsRuleSet"
    )

    operator_rate = rules["OperatorRouteRateLimit"]["Statement"]["RateBasedStatement"]
    assert operator_rate["AggregateKeyType"] == "IP"
    assert operator_rate["Limit"] == {"Ref": "OperatorRateLimit"}
    operator_match = operator_rate["ScopeDownStatement"]["ByteMatchStatement"]
    assert operator_match["SearchString"] == "/api/v1/operations/"
    assert operator_match["PositionalConstraint"] == "STARTS_WITH"

    public_rate = rules["PublicRouteRateLimit"]["Statement"]["RateBasedStatement"]
    assert public_rate["Limit"] == {"Ref": "PublicRateLimit"}
    assert "NotStatement" in public_rate["ScopeDownStatement"]
    assert all(
        rule["VisibilityConfig"]["SampledRequestsEnabled"] is False for rule in web_acl["Rules"]
    )

    logging = resources["WafLoggingConfiguration"]["Properties"]
    assert logging["LoggingFilter"] == {
        "DefaultBehavior": "DROP",
        "Filters": [
            {
                "Behavior": "KEEP",
                "Conditions": [
                    {"ActionCondition": {"Action": "BLOCK"}},
                    {"ActionCondition": {"Action": "COUNT"}},
                ],
                "Requirement": "MEETS_ANY",
            }
        ],
    }
    assert logging["RedactedFields"] == [
        {"SingleHeader": {"Name": "authorization"}},
        {"SingleHeader": {"Name": "cookie"}},
    ]
    assert resources["WafLogGroup"]["Properties"]["LogGroupName"].startswith("aws-waf-logs-")
    association = resources["ApiWebAclAssociation"]["Properties"]
    assert association["ResourceArn"] == {"Ref": "ApiLoadBalancer"}


def test_outputs_supply_exact_oidc_application_configuration_shapes() -> None:
    outputs = _template()["Outputs"]

    assert outputs["CognitoClientId"]["Value"] == {"Ref": "OperatorUserPoolClient"}
    assert outputs["CognitoUserPoolId"]["Value"] == {"Ref": "OperatorUserPool"}
    issuer = outputs["CognitoIssuer"]["Value"]["Fn::Sub"]
    jwks = outputs["CognitoJwksUrl"]["Value"]["Fn::Sub"]
    assert issuer == "https://cognito-idp.${AWS::Region}.${AWS::URLSuffix}/${OperatorUserPool}"
    assert jwks == f"{issuer}/.well-known/jwks.json"
