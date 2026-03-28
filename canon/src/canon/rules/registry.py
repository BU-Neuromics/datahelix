"""RuleRegistry: find production rules matching entity type and parameters."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from canon.rules.models import FetchRule, ProductionRule, is_entity_ref, is_glob_wildcard, is_pure_wildcard

if TYPE_CHECKING:
    from canon.rules.dynamic_store import DynamicRule, DynamicRuleStore

_ENTITY_REF_RE = re.compile(r"^ref:([A-Za-z][A-Za-z0-9_]*)\{(.*)\}$")


def _parse_entity_ref_constraints(ref_str: str) -> dict[str, str]:
    """Parse 'ref:Type{a=b, c=d}' → {'a': 'b', 'c': 'd'}."""
    m = _ENTITY_REF_RE.match(ref_str)
    if not m:
        return {}
    constraints_str = m.group(2).strip()
    if not constraints_str:
        return {}
    result = {}
    for part in constraints_str.split(","):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
    return result


def _rule_param_is_fixed(value: Any) -> bool:
    """Return True if a rule produces.match value is a fixed (non-wildcard) value."""
    if not isinstance(value, str):
        return True  # non-string scalars are always fixed
    if is_glob_wildcard(value):
        return False
    if is_pure_wildcard(value):
        return False
    if is_entity_ref(value):
        # Entity ref is fixed only if it contains no wildcards
        constraints = _parse_entity_ref_constraints(value)
        return all(
            not (v.startswith("{") and v.endswith("}"))
            for v in constraints.values()
        )
    # Plain scalar string — fixed
    return True


def _rule_matches(
    rule: ProductionRule,
    entity_type: str,
    resolved_params: dict[str, Any],
) -> bool:
    """
    Return True if this rule can produce the requested entity.

    Matching rules:
    - rule.produces.entity_type == entity_type
    - For each fixed param in rule.produces.match:
        rule.produces.match[param] == resolved_params.get(param)
    - For each wildcard param in rule.produces.match:
        param key exists in resolved_params (any value)
    """
    if rule.produces.entity_type != entity_type:
        return False

    for param, rule_value in rule.produces.match.items():
        if is_glob_wildcard(rule_value):
            # Glob wildcard "*": accept any value, including absent fields.
            # Callers may omit this field entirely (partial specification matching).
            continue
        elif is_pure_wildcard(rule_value):
            # Named wildcard {name}: param must exist in resolved_params
            if param not in resolved_params:
                return False
        elif is_entity_ref(rule_value):
            # Entity ref: check if it's fixed (no wildcards inside)
            if _rule_param_is_fixed(rule_value):
                # Fixed entity ref: must match exactly (compare UUID to UUID)
                if resolved_params.get(param) != rule_value and param not in resolved_params:
                    return False
                # If the rule has a fixed ref and resolved_params has a UUID,
                # we can't compare them directly here — this is handled at resolution time.
                # For registry matching: if a UUID is present, we trust it matches
                # because entity refs in rules are resolved before registry lookup.
                # Actually: fixed entity refs in produces.match are pre-resolved to UUIDs
                # during rule loading for matching purposes. But we don't do that here.
                # Instead: if resolved_params has this param, it's already a UUID.
                # The rule's fixed ref will also have been resolved to a UUID.
                # For now: if the rule value is a fixed ref, require param to exist.
                if param not in resolved_params:
                    return False
            else:
                # Entity ref with wildcards: param must exist
                if param not in resolved_params:
                    return False
        else:
            # Fixed scalar: must match exactly
            request_val = resolved_params.get(param)
            if request_val is None:
                return False
            # Compare as strings for robustness
            if str(request_val) != str(rule_value):
                return False

    return True


def _rule_matches_fetch(
    rule: FetchRule,
    entity_type: str,
    resolved_params: dict,
) -> bool:
    """Return True if this fetch rule matches the requested entity type and params."""
    if rule.produces.entity_type != entity_type:
        return False
    for param, rule_value in rule.produces.match.items():
        request_val = resolved_params.get(param)
        if request_val is None:
            return False
        if str(request_val) != str(rule_value):
            return False
    return True


class RuleRegistry:
    """Registry of all production and fetch rules."""

    def __init__(
        self,
        rules: list[ProductionRule | FetchRule],
        dynamic_store: "DynamicRuleStore | None" = None,
    ) -> None:
        self._all_rules = rules
        self._rules: list[ProductionRule] = [r for r in rules if isinstance(r, ProductionRule)]
        self._fetch_rules: list[FetchRule] = [r for r in rules if isinstance(r, FetchRule)]
        # Index production rules by entity_type for fast lookup
        self._by_type: dict[str, list[ProductionRule]] = {}
        for rule in self._rules:
            self._by_type.setdefault(rule.produces.entity_type, []).append(rule)
        # Index fetch rules by entity_type
        self._fetch_by_type: dict[str, list[FetchRule]] = {}
        for rule in self._fetch_rules:
            self._fetch_by_type.setdefault(rule.produces.entity_type, []).append(rule)
        self._dynamic_store = dynamic_store

    @property
    def rules(self) -> list[ProductionRule]:
        return list(self._rules)

    def rules_for_entity_type(self, entity_type: str) -> list[ProductionRule]:
        """Return all rules that can produce the given entity type."""
        return list(self._by_type.get(entity_type, []))

    def find_rule(
        self,
        entity_type: str,
        resolved_params: dict[str, Any],
    ) -> ProductionRule | None:
        """
        Find the first production rule matching the entity type and resolved parameters.

        Args:
            entity_type: The Hippo entity type to produce.
            resolved_params: Parameters with all entity refs already resolved to UUIDs.

        Returns:
            The matching ProductionRule, or None if no rule matches.
        """
        for rule in self._by_type.get(entity_type, []):
            if _rule_matches(rule, entity_type, resolved_params):
                return rule
        return None

    def get_rule(self, name: str) -> ProductionRule | None:
        """Return a rule by name."""
        for rule in self._rules:
            if rule.name == name:
                return rule
        return None

    def find_fetch_rule(
        self,
        entity_type: str,
        resolved_params: dict,
    ) -> FetchRule | None:
        """Find a fetch rule matching entity type and resolved parameters."""
        for rule in self._fetch_by_type.get(entity_type, []):
            if _rule_matches_fetch(rule, entity_type, resolved_params):
                return rule
        return None

    def set_dynamic_store(self, store: "DynamicRuleStore") -> None:
        """Attach a DynamicRuleStore so dynamic rules are queryable."""
        self._dynamic_store = store

    def find_dynamic_rule(self, name: str) -> "DynamicRule | None":
        """Look up a dynamically registered rule by name.

        Returns None if no dynamic store is attached or the name is not found.
        """
        if self._dynamic_store is None:
            return None
        return self._dynamic_store.get(name)
