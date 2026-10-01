"""Immutable raw-object storage boundary."""

from watchtower.storage.base import ObjectCollisionError, ObjectStore, StoredObject
from watchtower.storage.local import LocalObjectStore, UnsafeObjectKeyError

__all__ = [
    "LocalObjectStore",
    "ObjectCollisionError",
    "ObjectStore",
    "StoredObject",
    "UnsafeObjectKeyError",
]
