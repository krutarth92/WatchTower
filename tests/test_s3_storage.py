import os
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError
from pydantic import SecretStr, ValidationError

from watchtower.core.config import Settings
from watchtower.storage.base import (
    ObjectCollisionError,
    ObjectNotFoundError,
    ObjectStorageUnavailableError,
    StoredObjectTooLargeError,
    UnsafeObjectKeyError,
)
from watchtower.storage.factory import build_object_store
from watchtower.storage.local import LocalObjectStore
from watchtower.storage.s3 import S3ObjectStore


def client_error(code: str, status: int, operation: str) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": "sensitive upstream detail"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        operation,
    )


def make_store(client: MagicMock, *, max_bytes: int = 1024) -> S3ObjectStore:
    return S3ObjectStore(
        client,
        bucket="watchtower-raw-example",
        kms_key_id="arn:aws:kms:ap-south-1:111122223333:key/example",
        max_bytes=max_bytes,
    )


def test_s3_put_get_exists_and_list_preserve_immutable_contract() -> None:
    client = MagicMock()
    client.get_object.return_value = {"ContentLength": 7, "Body": BytesIO(b"content")}
    client.head_object.return_value = {}
    paginator = client.get_paginator.return_value
    paginator.paginate.return_value = [
        {"Contents": [{"Key": "raw/source/content.json"}]},
        {"Contents": []},
    ]
    store = make_store(client)

    stored = store.put_if_absent("raw/source/content.json", b"content")

    assert stored.uri == "s3://watchtower-raw-example/raw/source/content.json"
    assert stored.size_bytes == 7
    assert store.get(stored.key) == b"content"
    assert store.exists(stored.key) is True
    assert list(store.iter_keys("raw")) == [stored.key]
    put = client.put_object.call_args.kwargs
    assert put["IfNoneMatch"] == "*"
    assert put["ServerSideEncryption"] == "aws:kms"
    assert put["SSEKMSKeyId"].endswith("key/example")
    assert "ChecksumSHA256" in put
    paginator.paginate.assert_called_once_with(Bucket="watchtower-raw-example", Prefix="raw/")


def test_s3_existing_matching_content_is_idempotent_and_collision_fails() -> None:
    client = MagicMock()
    client.put_object.side_effect = client_error("PreconditionFailed", 412, "PutObject")
    client.get_object.return_value = {"ContentLength": 4, "Body": BytesIO(b"same")}
    store = make_store(client)

    assert store.put_if_absent("raw/source/item.bin", b"same").size_bytes == 4

    client.get_object.return_value = {"ContentLength": 9, "Body": BytesIO(b"different")}
    with pytest.raises(ObjectCollisionError):
        store.put_if_absent("raw/source/item.bin", b"same")


def test_s3_bounds_key_validation_and_sanitized_errors() -> None:
    client = MagicMock()
    store = make_store(client, max_bytes=4)

    with pytest.raises(UnsafeObjectKeyError):
        store.put_if_absent("../unsafe", b"data")
    with pytest.raises(StoredObjectTooLargeError):
        store.put_if_absent("raw/large.bin", b"large")

    client.get_object.return_value = {"ContentLength": 5, "Body": BytesIO(b"large")}
    with pytest.raises(StoredObjectTooLargeError):
        store.get("raw/large.bin")

    client.head_object.side_effect = client_error("NoSuchKey", 404, "HeadObject")
    assert store.exists("raw/missing.bin") is False
    client.get_object.side_effect = client_error("NoSuchKey", 404, "GetObject")
    with pytest.raises(ObjectNotFoundError, match="does not exist"):
        store.get("raw/missing.bin")

    client.get_object.side_effect = client_error("AccessDenied", 403, "GetObject")
    with pytest.raises(ObjectStorageUnavailableError) as caught:
        store.get("raw/private.bin")
    assert "sensitive" not in str(caught.value)

    client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "raw/../unsafe.bin"}]}
    ]
    with pytest.raises(ObjectStorageUnavailableError):
        list(store.iter_keys("raw"))


def test_storage_factory_uses_local_or_injected_s3_client(tmp_path: Path) -> None:
    local_settings = Settings(  # pyright: ignore[reportCallIssue]
        _env_file=None,  # pyright: ignore[reportCallIssue]
        database_url=SecretStr("postgresql+psycopg://user:secret@localhost/watchtower"),
        raw_storage_path=tmp_path,
    )
    assert isinstance(build_object_store(local_settings), LocalObjectStore)

    s3_settings = Settings(  # pyright: ignore[reportCallIssue]
        _env_file=None,  # pyright: ignore[reportCallIssue]
        database_url=SecretStr("postgresql+psycopg://user:secret@localhost/watchtower"),
        raw_storage_backend="s3",
        s3_bucket="watchtower-raw-example",
        s3_region="ap-south-1",
        s3_kms_key_id="alias/watchtower-raw",
    )
    assert isinstance(build_object_store(s3_settings, s3_client=MagicMock()), S3ObjectStore)


def test_s3_configuration_is_complete_and_production_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = SecretStr("postgresql+psycopg://user:secret@localhost/watchtower")
    with pytest.raises(ValidationError, match="S3 object storage requires"):
        Settings(  # pyright: ignore[reportCallIssue]
            _env_file=None,  # pyright: ignore[reportCallIssue]
            database_url=database_url,
            raw_storage_backend="s3",
        )

    production = {
        "environment": "production",
        "operator_auth_mode": "oidc",
        "oidc_issuer": "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_example",
        "oidc_jwks_url": (
            "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_example/.well-known/jwks.json"
        ),
        "oidc_client_id": "watchtower-client",
        "trusted_hosts": ["api.watchtower.example"],
        "proxy_trusted_hosts": ["10.0.0.0/16"],
    }
    with pytest.raises(ValidationError, match="RAW_STORAGE_BACKEND=s3"):
        Settings(
            _env_file=None,  # pyright: ignore[reportCallIssue]
            database_url=database_url,
            **production,
        )

    with pytest.raises(ValidationError, match="sslmode=verify-full"):
        Settings(  # pyright: ignore[reportCallIssue]
            _env_file=None,  # pyright: ignore[reportCallIssue]
            database_url=database_url,
            raw_storage_backend="s3",
            s3_bucket="watchtower-raw-example",
            s3_region="ap-south-1",
            s3_kms_key_id="alias/watchtower-raw",
            **production,
        )

    configured = Settings(  # pyright: ignore[reportCallIssue]
        _env_file=None,  # pyright: ignore[reportCallIssue]
        database_url=SecretStr(
            "postgresql+psycopg://runtime:secret@database.example/watchtower"
            "?sslmode=verify-full&sslrootcert=/etc/ssl/certs/rds-global-bundle.pem"
        ),
        raw_storage_backend="s3",
        s3_bucket="watchtower-raw-example",
        s3_region="ap-south-1",
        s3_kms_key_id="alias/watchtower-raw",
        **production,
    )
    assert configured.environment == "production"

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "static-key-is-forbidden")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "static-secret-is-forbidden")
    with pytest.raises(ValidationError, match="static AWS access-key"):
        Settings(  # pyright: ignore[reportCallIssue]
            _env_file=None,  # pyright: ignore[reportCallIssue]
            database_url=SecretStr(
                "postgresql+psycopg://runtime:secret@database.example/watchtower"
                "?sslmode=verify-full&sslrootcert=/etc/ssl/certs/rds-global-bundle.pem"
            ),
            raw_storage_backend="s3",
            s3_bucket="watchtower-raw-example",
            s3_region="ap-south-1",
            s3_kms_key_id="alias/watchtower-raw",
            **production,
        )


def test_s3_disposable_endpoint_preserves_immutable_contract() -> None:
    bucket = os.getenv("WATCHTOWER_TEST_S3_BUCKET")
    region = os.getenv("WATCHTOWER_TEST_S3_REGION")
    kms_key_id = os.getenv("WATCHTOWER_TEST_S3_KMS_KEY_ID")
    if not all((bucket, region, kms_key_id)):
        pytest.skip("disposable S3 integration environment is not configured")
    assert bucket is not None
    assert region is not None
    assert kms_key_id is not None

    client = boto3.client(
        "s3",
        region_name=region,
        endpoint_url=os.getenv("WATCHTOWER_TEST_S3_ENDPOINT_URL"),
        config=Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 2}),
    )
    store = S3ObjectStore(
        client,
        bucket=bucket,
        kms_key_id=kms_key_id,
        max_bytes=1024,
    )
    key = f"raw/integration/{uuid4()}.bin"

    created = store.put_if_absent(key, b"watchtower-s3-contract")

    assert created.uri == f"s3://{bucket}/{key}"
    assert store.put_if_absent(key, b"watchtower-s3-contract") == created
    assert store.get(key) == b"watchtower-s3-contract"
    assert store.exists(key) is True
    assert key in store.iter_keys("raw/integration")
    with pytest.raises(ObjectCollisionError):
        store.put_if_absent(key, b"conflicting-content")
