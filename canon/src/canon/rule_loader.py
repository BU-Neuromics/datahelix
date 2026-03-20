"""Loads and validates production rules from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from canon.exceptions import CanonValidationError
from canon.rules import ProductionRule


class RulesLoader:
    """Loads a list of ProductionRule objects from a YAML file."""

    def __init__(self, rules: list[ProductionRule]) -> None:
        self._rules = rules

    @classmethod
    def from_file(cls, path: str | Path) -> 'RulesLoader':
        """Parse rules from *path*.

        Collects all validation errors across all rules and raises a single
        CanonValidationError with a combined message if any are found.
        """
        p = Path(path)
        if not p.exists():
            raise CanonValidationError(f"Rules file not found: {path}")

        try:
            raw = yaml.safe_load(p.read_text())
        except yaml.YAMLError as exc:
            raise CanonValidationError(f"Invalid YAML in rules file {path}: {exc}") from exc

        if not isinstance(raw, list):
            raise CanonValidationError(f"Rules file {path} must contain a YAML list")

        rules: list[ProductionRule] = []
        errors: list[str] = []

        for i, entry in enumerate(raw):
            try:
                rules.append(ProductionRule.model_validate(entry))
            except ValidationError as exc:
                name = entry.get('name', f'<rule[{i}]>') if isinstance(entry, dict) else f'<rule[{i}]>'
                errors.append(f"Rule '{name}': {exc}")

        if errors:
            raise CanonValidationError(
                "Rule validation failed:\n" + "\n".join(errors)
            )

        return cls(rules)

    @property
    def rules(self) -> list[ProductionRule]:
        return list(self._rules)
