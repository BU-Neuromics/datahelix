"""EntityRefResolver: resolves ref:Type{field=val} expressions to Hippo entity IDs."""

from __future__ import annotations

import re
from typing import Any

from canon.exceptions import CanonPlanningError, CanonResolutionError
from canon.types import Entity, EntityRef

# Parses: ref:EntityType{field=val, other.nested=val2}
_REF_RE = re.compile(r"^ref:([A-Za-z][A-Za-z0-9_]*)\{([^}]*)\}$")
# Matches a wildcard placeholder: {name}
_WILDCARD_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def parse_entity_ref(expr: str) -> EntityRef:
    """
    Parse a ref: expression into an EntityRef.

    Examples::
        ref:ToolVersion{tool.name=STAR, version=2.7.10a}
        ref:GenomeBuild{name={genome_build}}
    """
    m = _REF_RE.match(expr)
    if not m:
        raise CanonPlanningError(
            f"Invalid entity reference expression: {expr!r}. "
            f"Expected format: ref:EntityType{{field=val, ...}}"
        )
    entity_type = m.group(1)
    constraints_str = m.group(2).strip()
    constraints: dict[str, str] = {}
    if constraints_str:
        for part in constraints_str.split(","):
            part = part.strip()
            if "=" not in part:
                raise CanonPlanningError(
                    f"Invalid constraint {part!r} in entity ref {expr!r}: expected 'field=value'"
                )
            key, _, val = part.partition("=")
            constraints[key.strip()] = val.strip()
    return EntityRef(entity_type=entity_type, constraints=constraints)


def _substitute_wildcards(value: str, bindings: dict[str, Any]) -> str:
    """Replace {name} placeholders in a value string from bindings."""

    def _replace(m: re.Match) -> str:
        name = m.group(1)
        if name not in bindings:
            raise CanonPlanningError(
                f"Unbound wildcard {{{name}}} in entity ref — no binding provided"
            )
        return str(bindings[name])

    return _WILDCARD_RE.sub(_replace, value)


def _get_nested(entity: Entity, dot_path: str) -> str | None:
    """
    Resolve a dot-notation path (up to 3 levels) against an entity's data dict.

    For 'tool.name', first check entity.data['tool'] and then access 'name' within it.
    For plain 'name', return entity.data['name'].
    """
    parts = dot_path.split(".", maxsplit=2)
    obj: Any = entity.data
    for part in parts:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
        if obj is None:
            return None
    return str(obj) if obj is not None else None


class EntityRefResolver:
    """
    Resolves ref:EntityType{field=val, ...} expressions to Hippo entity objects.

    Dot-notation constraints (e.g. tool.name=STAR) traverse the entity data up
    to 3 levels deep. Wildcards ({name}) are substituted from bindings before
    querying Hippo.
    """

    def __init__(self, hippo_client: Any) -> None:
        self._hippo = hippo_client

    def resolve(
        self,
        ref_expr: str,
        bindings: dict[str, Any] | None = None,
    ) -> Entity:
        """
        Resolve a ref: expression to exactly one Hippo entity.

        Args:
            ref_expr: e.g. 'ref:ToolVersion{tool.name=STAR, version=2.7.10a}'
            bindings: wildcard substitutions (e.g. {'genome_build': 'GRCh38'})

        Returns:
            The matching Entity.

        Raises:
            CanonPlanningError: unbound wildcard in the expression.
            CanonResolutionError: zero or more-than-one entity matches.
        """
        if bindings is None:
            bindings = {}

        entity_ref = parse_entity_ref(ref_expr)

        # Substitute wildcards in constraint values
        resolved_constraints: dict[str, str] = {}
        for key, val in entity_ref.constraints.items():
            resolved_constraints[key] = _substitute_wildcards(val, bindings)

        # Separate flat constraints (no dot) from dot-notation traversal constraints
        flat: dict[str, str] = {}
        nested: dict[str, str] = {}  # dot_path -> expected_value
        for key, val in resolved_constraints.items():
            if "." in key:
                nested[key] = val
            else:
                flat[key] = val

        # Fetch candidates using only flat constraints (Hippo API limitation)
        candidates = self._hippo.find_entities(entity_ref.entity_type, flat)

        if not candidates and nested:
            raise CanonResolutionError(
                f"No {entity_ref.entity_type} entities found matching {flat} "
                f"(before applying nested filters {nested})"
            )

        # Apply nested (dot-notation) filters in-memory
        if nested:
            filtered = []
            for entity in candidates:
                match = True
                for dot_path, expected in nested.items():
                    actual = _get_nested(entity, dot_path)
                    if actual != expected:
                        match = False
                        break
                if match:
                    filtered.append(entity)
            candidates = filtered

        if len(candidates) == 0:
            constraints_str = ", ".join(
                f"{k}={v}" for k, v in resolved_constraints.items()
            )
            raise CanonResolutionError(
                f"No {entity_ref.entity_type} entity found matching: {constraints_str}"
            )
        if len(candidates) > 1:
            constraints_str = ", ".join(
                f"{k}={v}" for k, v in resolved_constraints.items()
            )
            raise CanonResolutionError(
                f"Ambiguous ref: {len(candidates)} {entity_ref.entity_type} entities "
                f"match: {constraints_str}. Add more fields to disambiguate."
            )
        return candidates[0]
