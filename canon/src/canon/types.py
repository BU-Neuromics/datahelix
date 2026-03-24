"""Core types used throughout Canon."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EntityRef:
    """A parsed entity reference expression: ref:EntityType{field=val, ...}."""

    entity_type: str
    constraints: dict[str, str]  # field path → value (may contain wildcards like {name})

    def __repr__(self) -> str:
        parts = ", ".join(f"{k}={v}" for k, v in self.constraints.items())
        return f"ref:{self.entity_type}{{{parts}}}"


@dataclass
class WildcardBinding:
    """A single wildcard name → concrete value binding."""

    name: str
    value: Any


@dataclass
class Spec:
    """An artifact specification: entity type + resolved parameters."""

    entity_type: str
    params: dict[str, Any]

    def as_key(self) -> tuple:
        """Return a hashable key for cycle detection."""
        return (self.entity_type, frozenset(self.params.items()))


@dataclass
class ResolvedInput:
    """A resolved required input: binding name → entity URI and entity data."""

    bind: str
    uri: str
    entity_id: str
    entity_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Entity:
    """A Hippo entity record returned from the API."""

    id: str
    entity_type: str
    data: dict[str, Any]
    uri: str | None = None

    def __post_init__(self) -> None:
        # Ensure uri is populated from data if not set directly
        if self.uri is None and "uri" in self.data:
            self.uri = self.data["uri"]
