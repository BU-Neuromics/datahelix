"""Tests for RecursivePlanner."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from canon.resolver.planner import RecursivePlanner, PlanNode
from canon.rules.models import ProductionRule, ProducesSpec, ExecuteSpec
from canon.rules.registry import RuleRegistry
from canon.types import Entity, Spec
from canon.executors.base import CWLRunResult
from canon.exceptions import CanonCycleError, CanonNoRuleError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(entity_type="AlignedReads", eid="ent-uuid", uri="/data/test.bam"):
    return Entity(id=eid, entity_type=entity_type, data={"uri": uri}, uri=uri)


def _make_rule(name="r1", entity_type="AlignedReads", match=None):
    return ProductionRule(
        name=name,
        description="",
        produces=ProducesSpec(entity_type=entity_type, match=match or {"sample": "{sample}"}),
        requires=[],
        execute=ExecuteSpec(workflow="w.cwl", inputs={}),
    )


def _make_planner(hippo=None, registry=None, ref_resolver=None, executor=None, work_dir=None):
    hippo = hippo or MagicMock()
    registry = registry if registry is not None else RuleRegistry([])
    ref_resolver = ref_resolver or MagicMock()
    ref_resolver.resolve.return_value = _make_entity()
    return RecursivePlanner(
        hippo_client=hippo,
        rule_registry=registry,
        entity_ref_resolver=ref_resolver,
        executor=executor,
        work_dir_base=work_dir or "/tmp/canon-test-work",
    )


# ---------------------------------------------------------------------------
# REUSE path
# ---------------------------------------------------------------------------

def test_reuse_path_returns_uri():
    hippo = MagicMock()
    entity = _make_entity(uri="/data/test.bam")
    hippo.find_entity.return_value = entity

    planner = _make_planner(hippo=hippo)
    uri = planner.resolve("AlignedReads", {"sample": "S001"})
    assert uri == "/data/test.bam"
    hippo.find_entity.assert_called_once()


def test_reuse_path_no_rule_lookup_needed():
    """When entity exists in Hippo, registry.find_rule should NOT be called."""
    hippo = MagicMock()
    hippo.find_entity.return_value = _make_entity()
    registry = MagicMock()

    planner = _make_planner(hippo=hippo, registry=registry)
    planner.resolve("AlignedReads", {"sample": "S001"})
    registry.find_rule.assert_not_called()


# ---------------------------------------------------------------------------
# BUILD path
# ---------------------------------------------------------------------------

def test_build_path_calls_executor(tmp_path):
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule()
    registry = RuleRegistry([rule])

    executor = MagicMock()
    executor.run.return_value = CWLRunResult(exit_code=0, stdout="{}", stderr="", outputs={})

    output_entity = _make_entity()
    hippo.ingest_entity.return_value = output_entity

    planner = _make_planner(
        hippo=hippo,
        registry=registry,
        executor=executor,
        work_dir=str(tmp_path),
    )
    uri = planner.resolve("AlignedReads", {"sample": "S001"})
    executor.run.assert_called_once()
    assert uri == "/data/test.bam"


def test_build_path_inputs_resolved_from_rule(tmp_path):
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity()

    rule = _make_rule()
    registry = RuleRegistry([rule])

    executor = MagicMock()
    executor.run.return_value = CWLRunResult(exit_code=0, stdout="{}", stderr="", outputs={})

    planner = _make_planner(
        hippo=hippo,
        registry=registry,
        executor=executor,
        work_dir=str(tmp_path),
    )
    planner.resolve("AlignedReads", {"sample": "S001"})
    # executor.run called with (workflow, inputs, work_dir)
    call_args = executor.run.call_args
    assert call_args[0][0] == "w.cwl"


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

def test_cycle_detection_raises():
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule()
    registry = RuleRegistry([rule])
    planner = _make_planner(hippo=hippo, registry=registry)

    # Simulate the spec already being in progress
    spec = Spec(entity_type="AlignedReads", params={"sample": "S001"})
    planner._in_progress.add(spec.as_key())

    with pytest.raises(CanonCycleError):
        planner._resolve_internal("AlignedReads", {"sample": "S001"}, bindings={})


# ---------------------------------------------------------------------------
# CanonNoRuleError
# ---------------------------------------------------------------------------

def test_no_rule_raises_canon_no_rule_error():
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    registry = RuleRegistry([])  # no rules

    planner = _make_planner(hippo=hippo, registry=registry)
    with pytest.raises(CanonNoRuleError) as exc_info:
        planner.resolve("AlignedReads", {"sample": "S001"})
    assert exc_info.value.entity_type == "AlignedReads"


# ---------------------------------------------------------------------------
# plan() dry run
# ---------------------------------------------------------------------------

def test_plan_returns_reuse_node():
    hippo = MagicMock()
    entity = _make_entity(eid="ent-uuid", uri="/data/test.bam")
    hippo.find_entity.return_value = entity

    planner = _make_planner(hippo=hippo)
    node = planner.plan("AlignedReads", {"sample": "S001"})
    assert isinstance(node, PlanNode)
    assert node.decision == "REUSE"
    assert node.entity_id == "ent-uuid"
    assert node.uri == "/data/test.bam"
    assert node.entity_type == "AlignedReads"


def test_plan_returns_build_node_with_rule_name():
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule(name="r1")
    registry = RuleRegistry([rule])
    planner = _make_planner(hippo=hippo, registry=registry)
    node = planner.plan("AlignedReads", {"sample": "S001"})
    assert node.decision == "BUILD"
    assert node.rule_name == "r1"
    assert node.children == []


def test_plan_does_not_call_executor():
    """plan() must never invoke the executor."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule()
    registry = RuleRegistry([rule])
    executor = MagicMock()

    planner = _make_planner(hippo=hippo, registry=registry, executor=executor)
    planner.plan("AlignedReads", {"sample": "S001"})
    executor.run.assert_not_called()
