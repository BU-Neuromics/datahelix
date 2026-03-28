"""DynamicRule and DynamicRuleStore — runtime rule registration for Canon v0.2.

Dynamic rules are registered via the REST API and held in memory (v0.2).
Hippo entity storage is planned for v0.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DynamicProducesSpec:
    """Output specification for a dynamically registered rule."""

    entity_type: str
    match: dict[str, Any]
    from_output: str | None = None  # CWL output field name; None = inferred by convention


@dataclass
class DynamicRule:
    """A production rule registered at runtime via the Canon API.

    Analogous to ProductionRule but:
    - produces is a list (multi-entity CWL outputs are supported)
    - requires stores raw ref strings (resolved at execution time)
    - cwl_url points to a remote CWL document (no local workflow path)
    """

    name: str
    description: str
    produces: list[DynamicProducesSpec]
    requires: list[str]  # ref strings, e.g. 'CountsMatrix{id: "{counts_matrix_id}"}'
    cwl_url: str
    tags: list[str] = field(default_factory=list)


class DynamicRuleStore:
    """In-memory store for dynamically registered rules (Canon v0.2).

    Rules are keyed by name. Duplicate names are rejected.
    Thread safety is not guaranteed in v0.2.
    """

    def __init__(self) -> None:
        self._rules: dict[str, DynamicRule] = {}

    def register(self, rule: DynamicRule) -> None:
        """Register a rule. Raises ValueError if the name is already taken."""
        if rule.name in self._rules:
            raise ValueError(f"Rule '{rule.name}' is already registered")
        self._rules[rule.name] = rule

    def get(self, name: str) -> DynamicRule | None:
        """Look up a rule by name. Returns None if not found."""
        return self._rules.get(name)

    def has_name(self, name: str) -> bool:
        """Return True if a rule with this name has already been registered."""
        return name in self._rules

    def all_rules(self) -> list[DynamicRule]:
        """Return all registered rules."""
        return list(self._rules.values())

    def __len__(self) -> int:
        return len(self._rules)
