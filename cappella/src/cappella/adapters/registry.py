from typing import Any, TYPE_CHECKING

from cappella.adapters.base import ExternalSourceAdapter
from cappella.exceptions import ConfigError

if TYPE_CHECKING:
    from cappella.config import CappellaConfig


class AdapterRegistry:
    """Registry for external source adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, ExternalSourceAdapter] = {}
        self._adapter_classes: dict[str, type] = {}

    def register_class(self, adapter_type: str, cls: type) -> None:
        """Register an adapter class by type name."""
        self._adapter_classes[adapter_type] = cls

    def register(self, name: str, adapter: ExternalSourceAdapter) -> None:
        """Register an instantiated adapter by name."""
        self._adapters[name] = adapter

    @classmethod
    def from_config(cls, config: "CappellaConfig") -> "AdapterRegistry":
        """Build registry from config, discovering adapters via entry_points."""
        from importlib.metadata import entry_points

        registry = cls()

        # Discover registered adapter classes via entry points
        eps = entry_points(group="cappella.adapters")
        for ep in eps:
            try:
                adapter_cls = ep.load()
                registry.register_class(ep.name, adapter_cls)
            except Exception:
                pass

        # Also register built-in adapters directly (for when installed in dev mode)
        try:
            from cappella.adapters.csv_adapter import CSVAdapter
            registry.register_class("csv", CSVAdapter)
        except ImportError:
            pass
        try:
            from cappella.adapters.json_adapter import JSONAdapter
            registry.register_class("json", JSONAdapter)
        except ImportError:
            pass
        try:
            from cappella.adapters.xml_adapter import XMLAdapter
            registry.register_class("xml", XMLAdapter)
        except ImportError:
            pass
        try:
            from cappella.adapters.sql_adapter import SQLAdapter
            registry.register_class("sql", SQLAdapter)
        except ImportError:
            pass

        for adapter_name, adapter_cfg in config.adapters.items():
            adapter_type = adapter_cfg.type
            if adapter_type not in registry._adapter_classes:
                raise ConfigError(
                    f"AdapterRegistry: unknown adapter type '{adapter_type}' for '{adapter_name}'",
                    {"name": adapter_name, "type": adapter_type},
                )
            adapter_class = registry._adapter_classes[adapter_type]
            init_config = dict(adapter_cfg.config)
            init_config.setdefault("name", adapter_name)
            init_config.setdefault("trust_level", adapter_cfg.trust_level)
            instance = adapter_class(init_config)
            registry.register(adapter_name, instance)

        return registry

    def get(self, name: str) -> ExternalSourceAdapter:
        """Get an adapter by name."""
        if name not in self._adapters:
            raise ConfigError(f"AdapterRegistry: no adapter registered with name '{name}'")
        return self._adapters[name]

    def all(self) -> list[ExternalSourceAdapter]:
        """Return all registered adapters."""
        return list(self._adapters.values())

    def health_check_all(self) -> dict[str, dict]:
        """Run health_check on all adapters."""
        results: dict[str, dict] = {}
        for name, adapter in self._adapters.items():
            try:
                results[name] = adapter.health_check()
            except Exception as e:
                results[name] = {"status": "error", "detail": str(e)}
        return results
