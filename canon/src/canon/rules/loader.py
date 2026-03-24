"""RulesLoader: parse and validate canon_rules.yaml."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from canon.exceptions import CanonRuleValidationError
from canon.rules.models import (
    ExecuteSpec,
    InputBinding,
    ProductionRule,
    ProducesSpec,
    extract_wildcard_name,
    is_entity_ref,
    is_pure_wildcard,
)

# Regex to extract wildcards embedded inside strings, e.g. "{sample}" or parts of refs
_WILDCARD_IN_STR_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
# Regex for entity ref with wildcards: ref:Type{field={wc}, ...}
_ENTITY_REF_RE = re.compile(r"^ref:([A-Za-z][A-Za-z0-9_]*)\{(.*)\}$")


def _extract_wildcards_from_value(value: Any) -> set[str]:
    """Extract all {name} wildcard names from a value (string or nested)."""
    if not isinstance(value, str):
        return set()
    return {m.group(1) for m in _WILDCARD_IN_STR_RE.finditer(value)}


def _extract_wildcards_from_match(match: dict) -> set[str]:
    """Extract all wildcard names from a match dict."""
    names: set[str] = set()
    for v in match.values():
        names |= _extract_wildcards_from_value(v)
    return names


def _is_tool_ref_without_version(value: str) -> bool:
    """
    Return True if this is a ref: to a Tool type (not ToolVersion) — which is forbidden.
    Tool entity references must always use ToolVersion.
    """
    m = _ENTITY_REF_RE.match(value)
    if not m:
        return False
    entity_type = m.group(1)
    # Tool alone (not ToolVersion) is forbidden
    return entity_type == "Tool"


def _parse_match(raw: dict | None) -> dict[str, Any]:
    if raw is None:
        return {}
    return dict(raw)


def _parse_requires(raw_list: list | None) -> list[InputBinding]:
    if not raw_list:
        return []
    bindings = []
    for item in raw_list:
        bindings.append(
            InputBinding(
                bind=item["bind"],
                entity_type=item["entity_type"],
                match=_parse_match(item.get("match")),
            )
        )
    return bindings


def _parse_execute(raw: dict) -> ExecuteSpec:
    return ExecuteSpec(
        workflow=raw["workflow"],
        inputs=_parse_match(raw.get("inputs")),
    )


class RulesLoader:
    """Load and validate canon_rules.yaml into ProductionRule objects."""

    def __init__(self, rules_file: Path) -> None:
        self._rules_file = rules_file

    def load(self) -> list[ProductionRule]:
        """
        Parse and validate the rules file.

        Returns:
            List of validated ProductionRule objects.

        Raises:
            CanonRuleValidationError: if any validation check fails (all errors reported).
        """
        if not self._rules_file.exists():
            raise CanonRuleValidationError(
                f"Rules file not found: {self._rules_file}"
            )

        try:
            raw = yaml.safe_load(self._rules_file.read_text())
        except yaml.YAMLError as e:
            raise CanonRuleValidationError(
                f"YAML parse error in {self._rules_file}: {e}"
            ) from e

        if not isinstance(raw, dict) or "rules" not in raw:
            raise CanonRuleValidationError(
                f"{self._rules_file}: must be a YAML mapping with a 'rules' key"
            )

        raw_rules = raw["rules"]
        if not isinstance(raw_rules, list):
            raise CanonRuleValidationError(
                f"{self._rules_file}: 'rules' must be a YAML list"
            )

        errors: list[str] = []
        rules: list[ProductionRule] = []

        for i, raw_rule in enumerate(raw_rules):
            try:
                rule = self._parse_rule(raw_rule, i)
                rules.append(rule)
            except (KeyError, TypeError, ValueError) as e:
                name = raw_rule.get("name", f"<rule[{i}]>") if isinstance(raw_rule, dict) else f"<rule[{i}]>"
                errors.append(f"Rule '{name}': {e}")

        # Cross-rule validation
        cross_errors = self._validate_cross_rule(rules)
        errors.extend(cross_errors)

        # Per-rule semantic validation
        for rule in rules:
            rule_errors = self._validate_rule_semantics(rule)
            errors.extend(rule_errors)

        if errors:
            error_msg = f"Rule validation failed ({len(errors)} error(s)):\n"
            error_msg += "\n".join(f"  - {e}" for e in errors)
            raise CanonRuleValidationError(error_msg)

        return rules

    def _parse_rule(self, raw: dict, index: int) -> ProductionRule:
        """Parse a single rule dict into a ProductionRule."""
        if not isinstance(raw, dict):
            raise ValueError(f"Rule must be a mapping, got {type(raw).__name__}")

        name = raw.get("name")
        if not name:
            raise ValueError(f"Rule at index {index} is missing 'name'")

        produces_raw = raw.get("produces")
        if not produces_raw:
            raise ValueError("Missing 'produces' block")

        execute_raw = raw.get("execute")
        if not execute_raw:
            raise ValueError("Missing 'execute' block")

        return ProductionRule(
            name=str(name),
            description=str(raw.get("description", "")),
            produces=ProducesSpec(
                entity_type=produces_raw["entity_type"],
                match=_parse_match(produces_raw.get("match")),
            ),
            requires=_parse_requires(raw.get("requires")),
            execute=_parse_execute(execute_raw),
        )

    def _validate_cross_rule(self, rules: list[ProductionRule]) -> list[str]:
        """Check for duplicate rule names and duplicate produces specs."""
        errors: list[str] = []
        seen_names: set[str] = set()
        seen_produces: dict[tuple, str] = {}

        for rule in rules:
            if rule.name in seen_names:
                errors.append(f"Duplicate rule name: '{rule.name}'")
            seen_names.add(rule.name)

            produces_key = (
                rule.produces.entity_type,
                frozenset(rule.produces.match.items()),
            )
            if produces_key in seen_produces:
                errors.append(
                    f"Rule '{rule.name}': ambiguous produces — same entity_type and match "
                    f"as rule '{seen_produces[produces_key]}'"
                )
            seen_produces[produces_key] = rule.name

        return errors

    def _validate_rule_semantics(self, rule: ProductionRule) -> list[str]:
        """Validate a single rule's semantics."""
        errors: list[str] = []
        rules_dir = self._rules_file.parent

        # CWL workflow file must exist
        cwl_path = rules_dir / rule.execute.workflow
        if not cwl_path.exists():
            errors.append(
                f"Rule '{rule.name}': workflow not found: {rule.execute.workflow}"
            )

        # Sidecar must exist alongside CWL
        sidecar_path = cwl_path.with_suffix("").with_suffix(".canon.yaml")
        if not sidecar_path.exists():
            # Try .canon.yaml appended directly
            sidecar_path2 = Path(str(cwl_path) + ".canon.yaml").parent / (
                cwl_path.stem + ".canon.yaml"
            )
            if not sidecar_path2.exists():
                errors.append(
                    f"Rule '{rule.name}': sidecar not found: "
                    f"{cwl_path.stem}.canon.yaml alongside {rule.execute.workflow}"
                )

        # Tool entity references must use ToolVersion, not Tool
        for param, value in rule.produces.match.items():
            if isinstance(value, str) and _is_tool_ref_without_version(value):
                errors.append(
                    f"Rule '{rule.name}': param '{param}': "
                    f"entity references to Tool must use ToolVersion (tool version required)"
                )

        # Wildcards in requires.match must appear in produces.match
        produces_wildcards = _extract_wildcards_from_match(rule.produces.match)
        for req in rule.requires:
            req_wildcards = _extract_wildcards_from_match(req.match)
            unpropagated = req_wildcards - produces_wildcards
            if unpropagated:
                errors.append(
                    f"Rule '{rule.name}': requires[{req.bind}]: "
                    f"wildcard(s) not propagated to produces.match: "
                    + ", ".join(f"{{{w}}}" for w in sorted(unpropagated))
                )

        # Input expressions must reference known bindings or wildcards
        known_binds = {req.bind for req in rule.requires}
        all_wildcards = _extract_wildcards_from_match(rule.produces.match)

        for cwl_input, expr in rule.execute.inputs.items():
            if not isinstance(expr, str):
                continue
            # Find {binding.field} style references
            for m in _WILDCARD_IN_STR_RE.finditer(expr):
                name = m.group(1)
                # Could be a wildcard name or a binding name (binding.field is handled at runtime)
                # Just check that it's either a known wildcard or binding base name
                base = name.split(".")[0] if "." in name else name
                if base not in known_binds and base not in all_wildcards:
                    errors.append(
                        f"Rule '{rule.name}': execute.inputs.{cwl_input}: "
                        f"unknown binding or wildcard '{{{name}}}'"
                    )

        return errors
