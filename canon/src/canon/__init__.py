"""Canon — Semantic artifact resolver for BASS."""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"


def resolve(*, entity_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Module-level convenience for in-process Canon resolution.

    Used by Cappella's CanonClient in ``in_process`` mode::

        import canon
        result = canon.resolve(entity_type="GeneCounts", params={...})
        # result == {"decision": "REUSE", "uri": "s3://..."}

    Loads config from ``canon.yaml`` in cwd, builds a RecursivePlanner,
    and delegates to ``resolve_with_decision()``.

    Returns:
        Dict with ``decision`` (REUSE|BUILD|FETCH|AGGREGATE) and ``uri``.

    Raises:
        CanonConfigError: if canon.yaml is missing or invalid.
        CanonNoRuleError: if no rule exists to produce the entity.
    """
    from canon.config import CanonConfig
    from canon.resolver.planner import RecursivePlanner
    from canon.rules.loader import load_rules
    from canon.rules.registry import RuleRegistry

    config = CanonConfig.load()

    # Build minimal components for resolution
    from canon.resolver.hippo_client import HippoHttpClient
    from canon.resolver.entity_ref import EntityRefResolver

    hippo = HippoHttpClient(config.hippo_url, config.hippo_token)
    rules = load_rules(config.resolve_rules_file(config._config_dir or __import__("pathlib").Path.cwd()))
    registry = RuleRegistry(rules)
    ref_resolver = EntityRefResolver(hippo)

    planner = RecursivePlanner(
        hippo_client=hippo,
        rule_registry=registry,
        entity_ref_resolver=ref_resolver,
        work_dir_base=str(config.resolve_work_dir(config._config_dir or __import__("pathlib").Path.cwd())),
    )
    return planner.resolve_with_decision(entity_type, params)
