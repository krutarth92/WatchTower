"""Immutable raw-object storage boundary."""

from watchtower.storage.base import (
    ObjectCollisionError,
    ObjectNotFoundError,
    ObjectStorageError,
    ObjectStorageUnavailableError,
    ObjectStore,
    StoredObject,
    StoredObjectTooLargeError,
    UnsafeObjectKeyError,
)
from watchtower.storage.local import LocalObjectStore
from watchtower.storage.s3 import S3ObjectStore

__all__ = [
    "LocalObjectStore",
    "ObjectCollisionError",
    "ObjectNotFoundError",
    "ObjectStorageError",
    "ObjectStorageUnavailableError",
    "ObjectStore",
    "StoredObject",
    "StoredObjectTooLargeError",
    "S3ObjectStore",
    "UnsafeObjectKeyError",
]
