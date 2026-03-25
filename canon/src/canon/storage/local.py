"""LocalStorageAdapter — filesystem (and NFS) storage backend."""

from __future__ import annotations

import shutil
from pathlib import Path

from canon.exceptions import CanonStorageError
from canon.storage.base import StorageAdapter


def _resolve_path(uri: str) -> Path:
    """Strip file:// prefix and return a Path."""
    if uri.startswith("file://"):
        return Path(uri[len("file://"):])
    return Path(uri)


class LocalStorageAdapter(StorageAdapter):
    """Storage adapter for local filesystems and NFS/shared storage.

    Handles file:// URIs and bare paths (empty scheme).
    """

    name = "local"
    uri_schemes = ["file", ""]

    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)

    def put(self, local_path: str | Path, dest_uri: str) -> str:
        """Copy a local file to dest_uri, creating parent dirs as needed.

        Returns:
            file:// URI of the destination.

        Raises:
            CanonStorageError: if source file not found or copy fails.
        """
        src = Path(local_path)
        if not src.exists():
            raise CanonStorageError(
                f"Source file not found: {src}"
            )

        dest = _resolve_path(dest_uri)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src, dest)
        except OSError as e:
            raise CanonStorageError(f"Failed to copy {src} → {dest}: {e}") from e

        return f"file://{dest}"

    def get(self, uri: str, local_dir: str | Path) -> Path:
        """Return the local path for a file URI, copying if needed.

        For shared/NFS filesystems: returns the path directly if accessible.

        Raises:
            CanonStorageError: if the file cannot be found.
        """
        path = _resolve_path(uri)
        if path.exists():
            return path
        raise CanonStorageError(f"File not found at URI: {uri}")

    def exists(self, uri: str) -> bool:
        """Return True if the URI resolves to an existing filesystem path."""
        return _resolve_path(uri).exists()

    def build_dest_uri(self, entity_type: str, entity_id: str, filename: str) -> str:
        """Construct a destination URI.

        Format: file://<base_path>/<entity_type_lower>/<entity_id>/<filename>
        """
        dest = self._base_path / entity_type.lower() / entity_id / filename
        return f"file://{dest}"
