import os
import re
import tempfile
from pathlib import Path, PurePosixPath

from watchtower.storage.base import (
    ObjectCollisionError,
    StoredObject,
    StoredObjectTooLargeError,
)

SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class UnsafeObjectKeyError(ValueError):
    """Object key could escape or cannot be represented safely."""


class LocalObjectStore:
    def __init__(self, root: Path, max_bytes: int) -> None:
        self._root = root.resolve()
        self._max_bytes = max_bytes

    def put_if_absent(self, key: str, content: bytes) -> StoredObject:
        if len(content) > self._max_bytes:
            raise StoredObjectTooLargeError(
                f"Object has {len(content)} bytes; limit is {self._max_bytes}"
            )
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            self._require_matching_content(target, content)
            return self._reference(key, target)

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            try:
                os.link(temporary_path, target)
            except FileExistsError:
                self._require_matching_content(target, content)
            return self._reference(key, target)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def get(self, key: str) -> bytes:
        target = self._resolve(key)
        content = target.read_bytes()
        if len(content) > self._max_bytes:
            raise StoredObjectTooLargeError(
                f"Stored object has {len(content)} bytes; limit is {self._max_bytes}"
            )
        return content

    def exists(self, key: str) -> bool:
        target = self._resolve(key)
        return target.is_file()

    def _resolve(self, key: str) -> Path:
        if "\\" in key:
            raise UnsafeObjectKeyError("Object keys must use forward slashes")
        pure = PurePosixPath(key)
        if pure.is_absolute() or not pure.parts:
            raise UnsafeObjectKeyError("Object keys must be relative")
        if any(part in {"", ".", ".."} or not SAFE_SEGMENT.fullmatch(part) for part in pure.parts):
            raise UnsafeObjectKeyError("Object key contains an unsafe path segment")
        target = self._root.joinpath(*pure.parts).resolve()
        if not target.is_relative_to(self._root):
            raise UnsafeObjectKeyError("Object key escapes the storage root")
        return target

    @staticmethod
    def _require_matching_content(target: Path, content: bytes) -> None:
        if not target.is_file() or target.read_bytes() != content:
            raise ObjectCollisionError("Object key already exists with different content")

    @staticmethod
    def _reference(key: str, target: Path) -> StoredObject:
        return StoredObject(key=key, uri=target.as_uri(), size_bytes=target.stat().st_size)
