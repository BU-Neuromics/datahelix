"""StorageAdapter ABC — behavioral contract for all storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    """Abstract base class for Canon storage backends.

    Subclasses must declare:
        name: str          — entry point name (e.g. "local")
        uri_schemes: list  — URI schemes handled (e.g. ["file", ""])
    """

    name: str
    uri_schemes: list[str]

    @abstractmethod
    def put(self, local_path: str | Path, dest_uri: str) -> str:
        """Copy/upload a local file to permanent storage.

        Args:
            local_path: Path to the local file to upload.
            dest_uri: Destination URI (scheme depends on adapter).

        Returns:
            Canonical URI of the stored file.

        Raises:
            CanonStorageError: on any storage failure.
        """

    @abstractmethod
    def get(self, uri: str, local_dir: str | Path) -> Path:
        """Stage a file from storage to a local directory.

        Args:
            uri: URI of the file to retrieve.
            local_dir: Local directory to stage the file into.

        Returns:
            Local Path to the staged file.

        Raises:
            CanonStorageError: if the file cannot be staged.
        """

    @abstractmethod
    def exists(self, uri: str) -> bool:
        """Check whether a URI is accessible.

        Returns True if accessible, False otherwise. Never raises.
        """

    def build_dest_uri(self, entity_type: str, entity_id: str, filename: str) -> str:
        """Construct a destination URI for a given entity and filename.

        Subclasses should override this with backend-specific URI conventions.

        Raises:
            NotImplementedError: if not overridden by the subclass.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement build_dest_uri()"
        )
