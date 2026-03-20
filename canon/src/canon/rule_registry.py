"""Rules engine — lookup and validation of production rules."""

from __future__ import annotations

from canon.exceptions import CanonValidationError
from canon.rules import ProductionRule


class RulesEngine:
    """Registry and query interface for production rules."""

    def __init__(self, rules: list[ProductionRule]) -> None:
        self._rules = list(rules)

    @property
    def rules(self) -> list[ProductionRule]:
        return list(self._rules)

    def find_rules(
        self,
        entity_type: str,
        metadata_spec: dict | None = None,  # noqa: ARG002  (reserved for future filtering)
    ) -> list[ProductionRule]:
        """Return rules whose produces.entity_type matches *entity_type*.

        Metadata filtering is deferred to v0.2; all matching rules are returned.
        """
        return [r for r in self._rules if r.produces.entity_type == entity_type]

    def validate(self) -> None:
        """Raise CanonValidationError if any rule names are duplicated."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for rule in self._rules:
            if rule.name in seen:
                duplicates.append(rule.name)
            seen.add(rule.name)
        if duplicates:
            raise CanonValidationError(
                f"Duplicate rule names: {', '.join(sorted(duplicates))}"
            )
