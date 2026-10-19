from typing import Any

import boto3
from botocore.config import Config

from watchtower.core.config import Settings
from watchtower.storage.base import ObjectStore
from watchtower.storage.local import LocalObjectStore
from watchtower.storage.s3 import S3ObjectStore


def build_object_store(settings: Settings, *, s3_client: Any | None = None) -> ObjectStore:
    if settings.raw_storage_backend == "local":
        return LocalObjectStore(settings.raw_storage_path, settings.max_raw_evidence_bytes)

    client = s3_client
    if client is None:
        client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            config=Config(
                connect_timeout=settings.s3_request_timeout_seconds,
                read_timeout=settings.s3_request_timeout_seconds,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
    if settings.s3_bucket is None or settings.s3_kms_key_id is None:
        raise ValueError("S3 object storage requires a bucket and KMS key")
    return S3ObjectStore(
        client,
        bucket=settings.s3_bucket,
        kms_key_id=settings.s3_kms_key_id,
        max_bytes=settings.max_raw_evidence_bytes,
    )
