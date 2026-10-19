import json
from pathlib import Path


def test_durable_data_cloudformation_encodes_security_and_recovery_contract() -> None:
    path = Path("infra/aws/data-services.template.json")
    template = json.loads(path.read_text(encoding="utf-8"))
    resources = template["Resources"]

    bucket = resources["RawEvidenceBucket"]
    assert bucket["Properties"]["VersioningConfiguration"]["Status"] == "Enabled"
    assert bucket["Properties"]["ObjectLockConfiguration"]["Rule"]["DefaultRetention"] == {
        "Mode": "GOVERNANCE",
        "Days": {"Ref": "ObjectLockDays"},
    }
    assert all(bucket["Properties"]["PublicAccessBlockConfiguration"].values())

    runtime_statements = resources["RawEvidenceRuntimeRole"]["Properties"]["Policies"][0][
        "PolicyDocument"
    ]["Statement"]
    runtime_actions = {action for statement in runtime_statements for action in statement["Action"]}
    assert "s3:GetObject" in runtime_actions
    assert "s3:PutObject" in runtime_actions
    assert "s3:ListBucket" in runtime_actions
    assert not any("Delete" in action for action in runtime_actions)

    policy_statements = resources["RawEvidenceBucketPolicy"]["Properties"]["PolicyDocument"][
        "Statement"
    ]
    assert {statement["Sid"] for statement in policy_statements} >= {
        "DenyInsecureTransport",
        "DenyMissingOrIncorrectEncryption",
        "DenyIncorrectEncryptionKey",
    }

    database = resources["Database"]["Properties"]
    assert database["Engine"] == "postgres"
    assert database["MultiAZ"] is True
    assert database["PubliclyAccessible"] is False
    assert database["StorageEncrypted"] is True
    assert database["DeletionProtection"] is True
    assert database["BackupRetentionPeriod"] == 35
    assert resources["DatabaseParameterGroup"]["Properties"]["Parameters"]["rds.force_ssl"] == "1"

    vault = resources["BackupVault"]["Properties"]
    assert "AccessPolicy" not in vault
    assert "ChangeableForDays" not in vault["LockConfiguration"]
    backup_rule = resources["BackupPlan"]["Properties"]["BackupPlan"]["BackupPlanRule"][0]
    assert backup_rule["Lifecycle"]["DeleteAfterDays"] == {"Ref": "BackupRetentionDays"}
    assert resources["DatabaseRuntimeSecret"]["Type"] == "AWS::SecretsManager::Secret"
