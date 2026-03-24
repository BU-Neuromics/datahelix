"""RecursivePlanner: core resolution algorithm with cycle detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from canon.exceptions import (
    CanonCycleError,
    CanonExecutorError,
    CanonNoRuleError,
    CanonPlanningError,
)
from canon.rules.models import (
    InputBinding,
    ProductionRule,
    extract_wildcard_name,
    is_entity_ref,
    is_pure_wildcard,
)
from canon.types import Entity, ResolvedInput, Spec

logger = logging.getLogger(__name__)


@dataclass
class PlanNode:
    """A node in the resolution plan tree (dry-run output)."""

    entity_type: str
    params: dict[str, Any]
    decision: str  # 'REUSE' | 'BUILD'
    rule_name: str | None = None
    children: list["PlanNode"] = field(default_factory=list)
    entity_id: str | None = None
    uri: str | None = None


class RecursivePlanner:
    """
    Core Canon resolution algorithm.

    Phase 1: resolve entity refs in params via EntityRefResolver
    Phase 2: check Hippo for an existing entity (REUSE path)
    Phase 3: find a matching rule in RuleRegistry
    Phase 4: bind wildcards, detect cycles, resolve required inputs recursively, execute
    """

    def __init__(
        self,
        hippo_client: Any,
        rule_registry: Any,
        entity_ref_resolver: Any,
        executor: Any | None = None,
        ingestion_pipeline: Any | None = None,
        work_dir_base: str = ".canon/work",
    ) -> None:
        self._hippo = hippo_client
        self._registry = rule_registry
        self._ref_resolver = entity_ref_resolver
        self._executor = executor
        self._pipeline = ingestion_pipeline
        self._work_dir_base = work_dir_base
        self._in_progress: set[tuple] = set()  # spec keys (entity_type, frozenset(params))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, entity_type: str, params: dict[str, Any]) -> str:
        """
        Resolve an artifact to a URI, building it if necessary.

        Args:
            entity_type: Hippo entity type to resolve.
            params: Identity parameters for the artifact.

        Returns:
            URI string for the resolved entity.

        Raises:
            CanonResolutionError: entity ref or hippo query fails.
            CanonNoRuleError: no rule exists to build this artifact.
            CanonCycleError: circular dependency detected.
            CanonExecutorError: CWL execution failed.
            CanonIngestionError: output ingestion failed.
        """
        entity = self._resolve_internal(entity_type, params, bindings={})
        if entity.uri is None:
            raise CanonPlanningError(
                f"Resolved {entity_type} entity {entity.id} has no URI"
            )
        return entity.uri

    def plan(self, entity_type: str, params: dict[str, Any]) -> PlanNode:
        """
        Dry-run: compute the resolution plan without executing anything.

        Returns:
            PlanNode tree describing REUSE/BUILD decisions.
        """
        return self._plan_internal(entity_type, params, bindings={})

    # ------------------------------------------------------------------
    # Internal resolution
    # ------------------------------------------------------------------

    def _resolve_internal(
        self,
        entity_type: str,
        params: dict[str, Any],
        bindings: dict[str, Any],
    ) -> Entity:
        spec = Spec(entity_type=entity_type, params=params)
        spec_key = spec.as_key()

        # Cycle detection
        if spec_key in self._in_progress:
            path_str = " → ".join(
                f"{et}({dict(p)})" for et, p in self._in_progress
            )
            raise CanonCycleError(
                f"Circular dependency detected resolving {entity_type}: {path_str}",
                cycle_path=list(self._in_progress),
            )

        # Phase 1: resolve entity refs in params
        resolved_params = self._resolve_entity_refs_in_params(params, bindings)

        # Phase 2: check Hippo for existing entity (REUSE)
        existing = self._hippo.find_entity(entity_type, resolved_params)
        if existing is not None:
            logger.info("REUSE %s %s → %s", entity_type, resolved_params, existing.id)
            return existing

        # Phase 3: find matching rule
        rule = self._registry.find_rule(entity_type, resolved_params)
        if rule is None:
            available = self._registry.rules_for_entity_type(entity_type)
            raise CanonNoRuleError(entity_type, resolved_params, available=available)

        logger.info("BUILD %s %s using rule %s", entity_type, resolved_params, rule.name)

        # Phase 4: bind wildcards, resolve inputs, execute
        rule_bindings = self._bind_wildcards(rule, resolved_params, bindings)

        self._in_progress.add(spec_key)
        try:
            resolved_inputs = self._resolve_required_inputs(rule, rule_bindings)
            entity = self._execute_rule(rule, resolved_params, rule_bindings, resolved_inputs)
        finally:
            self._in_progress.discard(spec_key)

        return entity

    def _plan_internal(
        self,
        entity_type: str,
        params: dict[str, Any],
        bindings: dict[str, Any],
    ) -> PlanNode:
        spec = Spec(entity_type=entity_type, params=params)
        spec_key = spec.as_key()

        if spec_key in self._in_progress:
            raise CanonCycleError(
                f"Circular dependency in plan for {entity_type}",
            )

        resolved_params = self._resolve_entity_refs_in_params(params, bindings)

        existing = self._hippo.find_entity(entity_type, resolved_params)
        if existing is not None:
            return PlanNode(
                entity_type=entity_type,
                params=resolved_params,
                decision="REUSE",
                entity_id=existing.id,
                uri=existing.uri,
            )

        rule = self._registry.find_rule(entity_type, resolved_params)
        if rule is None:
            available = self._registry.rules_for_entity_type(entity_type)
            raise CanonNoRuleError(entity_type, resolved_params, available=available)

        rule_bindings = self._bind_wildcards(rule, resolved_params, bindings)

        self._in_progress.add(spec_key)
        try:
            children: list[PlanNode] = []
            for inp in rule.requires:
                child_params = self._build_input_params(inp, rule_bindings)
                child_node = self._plan_internal(inp.entity_type, child_params, rule_bindings)
                children.append(child_node)
        finally:
            self._in_progress.discard(spec_key)

        return PlanNode(
            entity_type=entity_type,
            params=resolved_params,
            decision="BUILD",
            rule_name=rule.name,
            children=children,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_entity_refs_in_params(
        self,
        params: dict[str, Any],
        bindings: dict[str, Any],
    ) -> dict[str, Any]:
        """Replace ref: values in params with entity IDs."""
        resolved: dict[str, Any] = {}
        for key, val in params.items():
            if is_entity_ref(val):
                entity = self._ref_resolver.resolve(val, bindings)
                resolved[key] = entity.id
            else:
                resolved[key] = val
        return resolved

    def _bind_wildcards(
        self,
        rule: ProductionRule,
        resolved_params: dict[str, Any],
        parent_bindings: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build the wildcard bindings dict for this rule invocation.

        Wildcards in produces.match are mapped to the corresponding param value.
        """
        bindings = dict(parent_bindings)
        for param_name, rule_val in rule.produces.match.items():
            if is_pure_wildcard(rule_val):
                wc_name = extract_wildcard_name(rule_val)
                if param_name in resolved_params:
                    bindings[wc_name] = resolved_params[param_name]
                else:
                    raise CanonPlanningError(
                        f"Rule {rule.name}: wildcard {{{wc_name}}} is mapped to parameter "
                        f"'{param_name}' but that parameter was not provided"
                    )
        return bindings

    def _build_input_params(
        self,
        inp: InputBinding,
        bindings: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve the parameter map for a required input binding."""
        params: dict[str, Any] = {}
        for param_name, rule_val in inp.match.items():
            if is_pure_wildcard(rule_val):
                wc_name = extract_wildcard_name(rule_val)
                if wc_name not in bindings:
                    raise CanonPlanningError(
                        f"Required input '{inp.bind}': unbound wildcard {{{wc_name}}}"
                    )
                params[param_name] = bindings[wc_name]
            elif is_entity_ref(rule_val):
                # Entity refs within required inputs are resolved via EntityRefResolver
                entity = self._ref_resolver.resolve(rule_val, bindings)
                params[param_name] = entity.id
            else:
                params[param_name] = rule_val
        return params

    def _resolve_required_inputs(
        self,
        rule: ProductionRule,
        bindings: dict[str, Any],
    ) -> list[ResolvedInput]:
        """Recursively resolve all required inputs for a rule."""
        resolved: list[ResolvedInput] = []
        for inp in rule.requires:
            child_params = self._build_input_params(inp, bindings)
            entity = self._resolve_internal(inp.entity_type, child_params, bindings)
            resolved.append(
                ResolvedInput(
                    bind=inp.bind,
                    uri=entity.uri or "",
                    entity_id=entity.id,
                    entity_data=entity.data,
                )
            )
        return resolved

    def _execute_rule(
        self,
        rule: ProductionRule,
        resolved_params: dict[str, Any],
        bindings: dict[str, Any],
        resolved_inputs: list[ResolvedInput],
    ) -> Entity:
        """Execute a rule's CWL workflow and ingest the output."""
        if self._executor is None:
            raise CanonExecutorError(
                f"No executor configured — cannot build {rule.produces.entity_type} "
                f"with rule {rule.name}"
            )

        import os
        import uuid
        from pathlib import Path

        run_id = str(uuid.uuid4())
        work_dir = Path(self._work_dir_base) / run_id
        work_dir.mkdir(parents=True, exist_ok=True)

        # Build CWL inputs from rule's execute.inputs expressions
        cwl_inputs = self._build_cwl_inputs(rule, bindings, resolved_inputs, resolved_params)

        cwl_result = self._executor.run(rule.execute.workflow, cwl_inputs, str(work_dir))

        if cwl_result.exit_code != 0:
            raise CanonExecutorError(
                f"Rule {rule.name} failed (exit {cwl_result.exit_code}): "
                f"{cwl_result.stderr[:500]}"
            )

        if self._pipeline is None:
            # No ingestion pipeline: create a minimal entity from params
            entity = self._hippo.ingest_entity(rule.produces.entity_type, resolved_params)
            return entity

        # Find sidecar file alongside CWL workflow
        cwl_path = Path(rule.execute.workflow)
        sidecar_path = cwl_path.with_suffix(".canon.yaml")

        output_entities = self._pipeline.ingest(
            cwl_result=cwl_result,
            sidecar_path=str(sidecar_path),
            cwl_inputs=cwl_inputs,
            rule_name=rule.name,
            bindings=bindings,
            work_dir=str(work_dir),
        )

        # Return the entity that matches what this rule produces
        target_type = rule.produces.entity_type
        if target_type in output_entities:
            return output_entities[target_type]

        # Fallback: ingest directly
        return self._hippo.ingest_entity(target_type, resolved_params)

    def _build_cwl_inputs(
        self,
        rule: ProductionRule,
        bindings: dict[str, Any],
        resolved_inputs: list[ResolvedInput],
        resolved_params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build CWL input dict from rule's execute.inputs expressions.

        Supported expressions:
          {bind.uri}   — the URI of a resolved input (bind name)
          {bind.id}    — the entity ID of a resolved input
          {param_name} — a wildcard or resolved parameter value
          scalar       — literal value
        """
        import re

        inputs_by_bind = {ri.bind: ri for ri in resolved_inputs}
        cwl_inputs: dict[str, Any] = {}

        _expr_re = re.compile(r"^\{([^}]+)\}$")

        for cwl_key, expr in rule.execute.inputs.items():
            if not isinstance(expr, str):
                cwl_inputs[cwl_key] = expr
                continue
            m = _expr_re.match(expr)
            if not m:
                cwl_inputs[cwl_key] = expr
                continue
            path = m.group(1)
            if "." in path:
                bind_name, attr = path.split(".", 1)
                if bind_name in inputs_by_bind:
                    ri = inputs_by_bind[bind_name]
                    if attr == "uri":
                        cwl_inputs[cwl_key] = ri.uri
                    elif attr == "id":
                        cwl_inputs[cwl_key] = ri.entity_id
                    else:
                        cwl_inputs[cwl_key] = ri.entity_data.get(attr)
                else:
                    cwl_inputs[cwl_key] = expr
            elif path in bindings:
                cwl_inputs[cwl_key] = bindings[path]
            elif path in resolved_params:
                cwl_inputs[cwl_key] = resolved_params[path]
            else:
                cwl_inputs[cwl_key] = expr

        return cwl_inputs
