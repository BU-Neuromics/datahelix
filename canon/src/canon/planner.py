"""Semantic planner — builds ExecutionPlan via DFS over production rules."""

from __future__ import annotations

from canon.config import CanonConfig
from canon.exceptions import CanonCycleError, CanonPlanningError
from canon.hippo_client import HippoClient
from canon.plan import CanonTask, EntityRef, ExecutionPlan, NodeDecision
from canon.resolver import resolve_wildcards
from canon.rule_registry import RulesEngine


class SemanticPlanner:
    """Recursively plans how to produce a requested entity."""

    def __init__(
        self,
        config: CanonConfig,
        hippo_client: HippoClient,
        rules_engine: RulesEngine,
    ) -> None:
        self._config = config
        self._hippo = hippo_client
        self._engine = rules_engine

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def plan(self, entity_type: str, metadata_spec: dict[str, str]) -> ExecutionPlan:
        """Return an ExecutionPlan for producing *entity_type* with *metadata_spec*."""
        nodes: list[EntityRef | CanonTask] = []
        grey: set[tuple[str, frozenset]] = set()
        self._dfs(entity_type, metadata_spec, nodes, grey, path=[])
        return ExecutionPlan(nodes=nodes)

    # ------------------------------------------------------------------
    # Internal DFS
    # ------------------------------------------------------------------

    def _dfs(
        self,
        entity_type: str,
        metadata_spec: dict[str, str],
        nodes: list[EntityRef | CanonTask],
        grey: set[tuple[str, frozenset]],
        path: list[str],
    ) -> None:
        key = (entity_type, frozenset(metadata_spec.items()))
        node_desc = f"{entity_type}({metadata_spec})"

        if key in grey:
            cycle_path = path + [node_desc]
            raise CanonCycleError(
                f"Dependency cycle detected: {' -> '.join(cycle_path)}",
                cycle_path=cycle_path,
            )

        # Check Hippo for an existing entity
        existing = self._hippo.query_entities(entity_type, metadata_spec)
        if existing:
            entity = existing[0]
            nodes.append(
                EntityRef(
                    entity_id=entity.get('id', ''),
                    entity_type=entity_type,
                    metadata=entity,
                    decision=NodeDecision.REUSE,
                )
            )
            return

        # Find a matching production rule
        matching = self._engine.find_rules(entity_type, metadata_spec)
        if not matching:
            raise CanonPlanningError(
                f"No rule found to produce entity_type='{entity_type}' "
                f"with metadata {metadata_spec}"
            )
        rule = matching[0]

        # Mark as in-progress (grey) before recursing
        grey.add(key)
        child_path = path + [node_desc]

        # Recursively plan each required input
        input_entities: dict[str, dict] = {}
        for binding in rule.requires:
            self._dfs(
                binding.entity_type,
                binding.metadata,
                nodes,
                grey,
                child_path,
            )
            # Grab the last resolved entity for wildcard resolution
            last = nodes[-1]
            if isinstance(last, EntityRef):
                input_entities[binding.bind] = last.metadata
            elif isinstance(last, CanonTask):
                # Represent the to-be-built entity by its output spec metadata
                input_entities[binding.bind] = {
                    spec.bind: spec.pattern for spec in last.output_spec
                }

        grey.discard(key)

        # Resolve wildcards
        wildcard_bindings = resolve_wildcards(rule, metadata_spec, input_entities)

        nodes.append(
            CanonTask(
                rule_name=rule.name,
                wildcard_bindings=wildcard_bindings,
                input_entities=input_entities,
                output_spec=rule.execute.outputs,
                decision=NodeDecision.BUILD,
            )
        )
