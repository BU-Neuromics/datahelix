"""Wildcard resolution for Canon production rules."""

from __future__ import annotations

from canon.exceptions import CanonPlanningError
from canon.rules import ProductionRule
from canon.types import WildcardBinding


def resolve_wildcards(
    rule: ProductionRule,
    request_spec: dict[str, str],
    input_entities: dict[str, dict],
) -> WildcardBinding:
    """Resolve all wildcards declared in *rule* into a WildcardBinding.

    Resolution order for each wildcard name:
    1. *request_spec* (caller-supplied values take precedence)
    2. Fields on any entity in *input_entities*
    3. Raises CanonPlanningError if still unbound
    """
    binding = WildcardBinding()

    for name in rule.wildcard_names:
        if name in request_spec:
            binding[name] = request_spec[name]
            continue

        resolved = False
        for entity in input_entities.values():
            if name in entity:
                binding[name] = str(entity[name])
                resolved = True
                break

        if not resolved:
            raise CanonPlanningError(
                f"Wildcard '{{{name}}}' in rule '{rule.name}' could not be resolved: "
                "not present in request_spec or any input entity"
            )

    return binding
