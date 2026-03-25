"""Canon storage adapter plugin system."""

from canon.storage.base import StorageAdapter
from canon.storage.local import LocalStorageAdapter
from canon.storage.registry import StorageAdapterRegistry

__all__ = ["StorageAdapter", "LocalStorageAdapter", "StorageAdapterRegistry"]
