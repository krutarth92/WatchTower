from dataclasses import dataclass
from typing import Protocol


class ObjectStorageError(Exception):
    """Base error for raw-object storage."""


class ObjectCollisionError(ObjectStorageError):
    """A key already exists with different bytes."""


class StoredObjectTooLargeError(ObjectStorageError):
    """Object exceeds the configured storage boundary."""


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    uri: str
    size_bytes: int


class ObjectStore(Protocol):
    def put_if_absent(self, key: str, content: bytes) -> StoredObject: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...
