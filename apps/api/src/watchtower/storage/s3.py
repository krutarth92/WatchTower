import base64
import hashlib
from collections.abc import Iterator
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from watchtower.storage.base import (
    ObjectCollisionError,
    ObjectNotFoundError,
    ObjectStorageUnavailableError,
    StoredObject,
    StoredObjectTooLargeError,
    UnsafeObjectKeyError,
    validate_object_key,
    validate_object_prefix,
)


class S3ObjectStore:
    """Private, immutable object storage backed by an S3-compatible client."""

    def __init__(
        self,
        client: Any,
        *,
        bucket: str,
        kms_key_id: str,
        max_bytes: int,
    ) -> None:
        self._client = client
        self._bucket = bucket
        self._kms_key_id = kms_key_id
        self._max_bytes = max_bytes

    def put_if_absent(self, key: str, content: bytes) -> StoredObject:
        validate_object_key(key)
        if len(content) > self._max_bytes:
            raise StoredObjectTooLargeError(
                f"Object has {len(content)} bytes; limit is {self._max_bytes}"
            )
        digest = base64.b64encode(hashlib.sha256(content).digest()).decode("ascii")
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentLength=len(content),
                ChecksumSHA256=digest,
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=self._kms_key_id,
                IfNoneMatch="*",
            )
        except ClientError as error:
            if self._is_precondition_failure(error):
                existing = self.get(key)
                if existing != content:
                    raise ObjectCollisionError(
                        "Object key already exists with different content"
                    ) from None
                return self._reference(key, len(existing))
            raise self._unavailable() from None
        except BotoCoreError:
            raise self._unavailable() from None
        return self._reference(key, len(content))

    def get(self, key: str) -> bytes:
        validate_object_key(key)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            content_length = response.get("ContentLength")
            if isinstance(content_length, int) and content_length > self._max_bytes:
                self._close_body(response.get("Body"))
                raise StoredObjectTooLargeError(
                    f"Stored object has {content_length} bytes; limit is {self._max_bytes}"
                )
            body = response["Body"]
            try:
                content = body.read(self._max_bytes + 1)
            finally:
                self._close_body(body)
        except ClientError as error:
            if self._is_not_found(error):
                raise ObjectNotFoundError("Object does not exist") from None
            raise self._unavailable() from None
        except (BotoCoreError, KeyError, OSError):
            raise self._unavailable() from None
        if len(content) > self._max_bytes:
            raise StoredObjectTooLargeError(f"Stored object has more than {self._max_bytes} bytes")
        return bytes(content)

    def exists(self, key: str) -> bool:
        validate_object_key(key)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as error:
            if self._is_not_found(error):
                return False
            raise self._unavailable() from None
        except BotoCoreError:
            raise self._unavailable() from None
        return True

    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        normalized_prefix = validate_object_prefix(prefix)
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self._bucket, Prefix=normalized_prefix)
            for page in pages:
                for item in page.get("Contents", []):
                    key = item.get("Key")
                    if isinstance(key, str):
                        validate_object_key(key)
                        yield key
        except ClientError:
            raise self._unavailable() from None
        except BotoCoreError:
            raise self._unavailable() from None
        except UnsafeObjectKeyError:
            raise self._unavailable() from None

    def _reference(self, key: str, size_bytes: int) -> StoredObject:
        return StoredObject(key=key, uri=f"s3://{self._bucket}/{key}", size_bytes=size_bytes)

    @staticmethod
    def _is_precondition_failure(error: ClientError) -> bool:
        metadata = error.response.get("ResponseMetadata", {})
        code = str(error.response.get("Error", {}).get("Code", ""))
        return metadata.get("HTTPStatusCode") == 412 or code in {
            "PreconditionFailed",
            "ConditionalRequestConflict",
        }

    @staticmethod
    def _is_not_found(error: ClientError) -> bool:
        metadata = error.response.get("ResponseMetadata", {})
        code = str(error.response.get("Error", {}).get("Code", ""))
        return metadata.get("HTTPStatusCode") == 404 or code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }

    @staticmethod
    def _close_body(body: Any) -> None:
        close = getattr(body, "close", None)
        if callable(close):
            close()

    @staticmethod
    def _unavailable() -> ObjectStorageUnavailableError:
        return ObjectStorageUnavailableError("Object storage operation failed")
