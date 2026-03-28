"""POST /api/v1/rules — dynamic rule registration endpoint."""

from __future__ import annotations

from typing import Any, Callable

try:
    from fastapi import APIRouter, Depends, HTTPException
    from pydantic import BaseModel, Field
except ImportError as _exc:
    raise ImportError(
        "fastapi is required for the Canon API. "
        "Install it with: pip install canon[api]"
    ) from _exc

from canon.rules.dynamic_store import DynamicProducesSpec, DynamicRule, DynamicRuleStore

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ProducesItem(BaseModel):
    """One entity produced by the rule's CWL workflow."""

    entity_type: str
    from_output: str | None = None
    match: dict[str, Any] = Field(default_factory=dict)


class RequiresItem(BaseModel):
    """A required input entity reference."""

    ref: str


class ExecuteConfig(BaseModel):
    """CWL execution specification for a dynamic rule."""

    cwl_url: str


class RegisterRuleRequest(BaseModel):
    """Payload for POST /api/v1/rules."""

    name: str
    produces: list[ProducesItem]
    requires: list[RequiresItem] = Field(default_factory=list)
    execute: ExecuteConfig
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class RegisterRuleResponse(BaseModel):
    """Response from POST /api/v1/rules on success."""

    name: str
    status: str = "registered"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

# Module-level default store — replaced via app.dependency_overrides in tests.
_default_store = DynamicRuleStore()


def get_rule_store() -> DynamicRuleStore:
    """Dependency: return the active DynamicRuleStore."""
    return _default_store


def _always_valid(entity_type: str) -> bool:
    """Default entity-type validator — always returns True (no Hippo connection)."""
    return True


def get_entity_type_validator() -> Callable[[str], bool]:
    """Dependency: return the entity-type existence checker.

    Override in tests or production to validate against the Hippo schema.
    """
    return _always_valid


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/rules", status_code=201, response_model=RegisterRuleResponse)
def register_rule(
    payload: RegisterRuleRequest,
    store: DynamicRuleStore = Depends(get_rule_store),
    entity_type_validator: Callable[[str], bool] = Depends(get_entity_type_validator),
) -> RegisterRuleResponse:
    """Register a new production rule at runtime.

    Validation:
    - ``name`` must be unique (409 on conflict)
    - Each ``produces[].entity_type`` must pass the entity_type_validator (422 on failure)
    - ``produces`` must contain at least one item
    - ``execute.cwl_url`` must be present (enforced by pydantic)
    """
    if not payload.produces:
        raise HTTPException(status_code=422, detail="'produces' must contain at least one item")

    if store.has_name(payload.name):
        raise HTTPException(
            status_code=409,
            detail=f"Rule '{payload.name}' is already registered",
        )

    for item in payload.produces:
        if not entity_type_validator(item.entity_type):
            raise HTTPException(
                status_code=422,
                detail=f"Entity type '{item.entity_type}' not found in Hippo schema",
            )

    rule = DynamicRule(
        name=payload.name,
        description=payload.description,
        produces=[
            DynamicProducesSpec(
                entity_type=item.entity_type,
                from_output=item.from_output,
                match=item.match,
            )
            for item in payload.produces
        ],
        requires=[item.ref for item in payload.requires],
        cwl_url=payload.execute.cwl_url,
        tags=payload.tags,
    )
    store.register(rule)

    return RegisterRuleResponse(name=payload.name)
