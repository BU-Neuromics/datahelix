"""StorageAdapterRegistry — entry-point discovery and URI-scheme routing."""

from __future__ import annotations

import importlib.metadata
from typing import Any

from canon.exceptions import CanonConfigError
from canon.storage.base import StorageAdapter


class StorageAdapterRegistry:
    """Discovers and routes to StorageAdapter implementations.

    Adapters are registered via the ``canon.storage_adapters`` entry point group.
    URI routing uses each adapter's ``uri_schemes`` class attribute.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, StorageAdapter] = {}
        self._scheme_map: dict[str, StorageAdapter] = {}
        self._default_type: str = ""

    @classmethod
    def load_from_entry_points(cls, config: Any) -> "StorageAdapterRegistry":
        """Discover all canon.storage_adapters entry points and instantiate adapters.

        Args:
            config: CanonConfig (or duck-typed equivalent) with output_storage.

        Returns:
            Populated StorageAdapterRegistry.

        Raises:
            CanonConfigError: if the configured output_storage.type is not installed.
        """
        registry = cls()
        registry._default_type = config.output_storage.type

        eps = importlib.metadata.entry_points(group="canon.storage_adapters")
        for ep in eps:
            adapter_cls = ep.load()
            # Pass adapter-specific extra fields from config (if any)
            extra: dict[str, Any] = {}
            if hasattr(config.output_storage, "model_extra") and config.output_storage.model_extra:
                extra = dict(config.output_storage.model_extra)
            # For LocalStorageAdapter, pass base_path if available
            if hasattr(config.output_storage, "base_path") and config.output_storage.base_path is not None:
                extra.setdefault("base_path", config.output_storage.base_path)

            try:
                instance: StorageAdapter = adapter_cls(**extra)
            except TypeError:
                instance = adapter_cls()

            registry._adapters[ep.name] = instance
            for scheme in instance.uri_schemes:
                registry._scheme_map[scheme] = instance

        if registry._default_type not in registry._adapters:
            available = list(registry._adapters.keys())
            raise CanonConfigError(
                f"canon.yaml: output_storage.type '{registry._default_type}' is not installed. "
                f"Available adapters: {available}. "
                f"Install the corresponding package (e.g., canon-storage-{registry._default_type})."
            )

        return registry

    def adapter_for_uri(self, uri: str) -> StorageAdapter:
        """Return the adapter responsible for the given URI.

        Args:
            uri: A URI string (e.g., ``file:///data/out.bam``, ``s3://bucket/key``, ``/bare/path``).

        Returns:
            The matching StorageAdapter instance.

        Raises:
            CanonConfigError: if no adapter is registered for the URI's scheme.
        """
        if "://" in uri:
            scheme = uri.split("://")[0]
        else:
            scheme = ""

        if scheme in self._scheme_map:
            return self._scheme_map[scheme]

        raise CanonConfigError(
            f"No storage adapter registered for URI scheme '{scheme}' "
            f"(URI: {uri}). Registered schemes: {list(self._scheme_map.keys())}."
        )

    @property
    def default_adapter(self) -> StorageAdapter:
        """Return the adapter configured as the default output storage backend."""
        return self._adapters[self._default_type]
