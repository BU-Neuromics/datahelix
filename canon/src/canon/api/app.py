"""Canon FastAPI application — dynamic rule registration + resolve API."""

from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as _exc:
    raise ImportError(
        "fastapi is required for the Canon API. "
        "Install it with: pip install canon[api]"
    ) from _exc

from canon.api.rules import router
from canon.exceptions import CanonNoRuleError

app = FastAPI(
    title="Canon API",
    description="Dynamic rule registration and runtime management for Canon.",
    version="0.2.0",
)

app.include_router(router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# /resolve endpoint — called by Cappella's CanonClient in HTTP mode
# ---------------------------------------------------------------------------


class ResolveRequest(BaseModel):
    """Payload for POST /resolve."""

    entity_type: str
    params: dict[str, Any] = Field(default_factory=dict)


class ResolveResponse(BaseModel):
    """Response from POST /resolve."""

    decision: str  # REUSE | BUILD | FETCH | AGGREGATE
    uri: str | None = None


# Module-level planner — initialised on first request via dependency.
_planner: Any = None


def _get_planner() -> Any:
    """Lazy-init a RecursivePlanner from canon.yaml."""
    global _planner
    if _planner is not None:
        return _planner

    from canon.config import CanonConfig
    from canon.resolver.entity_ref import EntityRefResolver
    from canon.resolver.hippo_client import HippoHttpClient
    from canon.resolver.planner import RecursivePlanner
    from canon.rules.loader import load_rules
    from canon.rules.registry import RuleRegistry

    config = CanonConfig.load()
    hippo = HippoHttpClient(config.hippo_url, config.hippo_token)
    rules_path = config.resolve_rules_file(
        config._config_dir or __import__("pathlib").Path.cwd()
    )
    rules = load_rules(rules_path)
    registry = RuleRegistry(rules)
    ref_resolver = EntityRefResolver(hippo)

    _planner = RecursivePlanner(
        hippo_client=hippo,
        rule_registry=registry,
        entity_ref_resolver=ref_resolver,
        work_dir_base=str(
            config.resolve_work_dir(
                config._config_dir or __import__("pathlib").Path.cwd()
            )
        ),
    )
    return _planner


@app.post("/resolve", response_model=ResolveResponse)
def resolve_entity(payload: ResolveRequest) -> ResolveResponse:
    """Resolve an artifact to a URI, returning the decision and URI.

    This is the primary integration point for Cappella's CanonClient in HTTP
    mode. Returns 200 with decision + URI on success, 404 when no rule
    matches the requested entity type and parameters.
    """
    planner = _get_planner()
    try:
        result = planner.resolve_with_decision(payload.entity_type, payload.params)
    except CanonNoRuleError:
        raise HTTPException(
            status_code=404,
            detail=f"No canon rule for entity_type '{payload.entity_type}'",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ResolveResponse(decision=result["decision"], uri=result.get("uri"))
