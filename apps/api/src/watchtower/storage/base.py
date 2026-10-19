from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath
from re import compile
from typing import Protocol

SAFE_SEGMENT = compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ObjectStorageError(Exception):
    """Base error for raw-object storage."""


class ObjectCollisionError(ObjectStorageError):
    """A key already exists with different bytes."""


class StoredObjectTooLargeError(ObjectStorageError):
    """Object exceeds the configured storage boundary."""


class ObjectStorageUnavailableError(ObjectStorageError):
    """The configured object store could not complete an operation."""


class ObjectNotFoundError(ObjectStorageError):
    """An object key does not exist in the configured store."""


class UnsafeObjectKeyError(ValueError):
    """Object key is absolute, traversing, or cannot be represented safely."""


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    uri: str
    size_bytes: int


class ObjectStore(Protocol):
    def put_if_absent(self, key: str, content: bytes) -> StoredObject: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def iter_keys(self, prefix: str = "") -> Iterator[str]: ...


def validate_object_key(key: str) -> PurePosixPath:
    if "\\" in key:
        raise UnsafeObjectKeyError("Object keys must use forward slashes")
    pure = PurePosixPath(key)
    if pure.is_absolute() or not pure.parts:
        raise UnsafeObjectKeyError("Object keys must be relative")
    if any(part in {"", ".", ".."} or not SAFE_SEGMENT.fullmatch(part) for part in pure.parts):
        raise UnsafeObjectKeyError("Object key contains an unsafe path segment")
    return pure


def validate_object_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    normalized = prefix.rstrip("/")
    validate_object_key(normalized)
    return f"{normalized}/"
