import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

from watchtower.storage.base import (
    ObjectCollisionError,
    ObjectNotFoundError,
    StoredObject,
    StoredObjectTooLargeError,
    UnsafeObjectKeyError,
    validate_object_key,
    validate_object_prefix,
)


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
        try:
            content = target.read_bytes()
        except FileNotFoundError:
            raise ObjectNotFoundError("Object does not exist") from None
        if len(content) > self._max_bytes:
            raise StoredObjectTooLargeError(
                f"Stored object has {len(content)} bytes; limit is {self._max_bytes}"
            )
        return content

    def exists(self, key: str) -> bool:
        target = self._resolve(key)
        return target.is_file()

    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        normalized_prefix = validate_object_prefix(prefix)
        search_root = self._root
        if normalized_prefix:
            search_root = self._resolve(normalized_prefix.rstrip("/"))
        if not search_root.exists():
            return
        for path in sorted(search_root.rglob("*")):
            if path.is_file():
                yield path.relative_to(self._root).as_posix()

    def _resolve(self, key: str) -> Path:
        pure = validate_object_key(key)
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
