"""Tests for SemanticPlanner."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from canon.config import CanonConfig
from canon.exceptions import CanonCycleError, CanonPlanningError
from canon.plan import CanonTask, EntityRef, NodeDecision
from canon.planner import SemanticPlanner
from canon.rule_registry import RulesEngine
from canon.rules import ProductionRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> CanonConfig:
    return CanonConfig(
        hippo_url="http://hippo.example.com",
        executor="local",
        rules_file="canon_rules.yaml",
    )


def _make_rule(
    name: str,
    produces_type: str,
    requires: list[dict] | None = None,
    metadata: dict | None = None,
) -> ProductionRule:
    d = {
        "name": name,
        "produces": {
            "entity_type": produces_type,
            "metadata": metadata or {},
        },
        "requires": requires or [],
        "execute": {
            "workflow": name,
            "inputs": {},
            "outputs": [],
        },
    }
    return ProductionRule.model_validate(d)


def _planner(rules: list[ProductionRule], hippo: MagicMock) -> SemanticPlanner:
    config = _make_config()
    engine = RulesEngine(rules)
    return SemanticPlanner(config, hippo, engine)


# ---------------------------------------------------------------------------
# Basic REUSE / BUILD
# ---------------------------------------------------------------------------


def test_reuse_when_entity_exists_in_hippo():
    hippo = MagicMock()
    hippo.query_entities.return_value = [{"id": "e-1", "aligner": "STAR"}]
    planner = _planner([], hippo)
    plan = planner.plan("AlignmentFile", {"aligner": "STAR"})
    assert len(plan.nodes) == 1
    node = plan.nodes[0]
    assert isinstance(node, EntityRef)
    assert node.decision == NodeDecision.REUSE
    assert node.entity_id == "e-1"


def test_build_when_no_entity_in_hippo():
    hippo = MagicMock()
    hippo.query_entities.return_value = []
    rule = _make_rule("align-with-star", "AlignmentFile")
    planner = _planner([rule], hippo)
    plan = planner.plan("AlignmentFile", {})
    assert len(plan.nodes) == 1
    node = plan.nodes[0]
    assert isinstance(node, CanonTask)
    assert node.decision == NodeDecision.BUILD
    assert node.rule_name == "align-with-star"


def test_no_rule_and_no_entity_raises_planning_error():
    hippo = MagicMock()
    hippo.query_entities.return_value = []
    planner = _planner([], hippo)
    with pytest.raises(CanonPlanningError):
        planner.plan("AlignmentFile", {})


# ---------------------------------------------------------------------------
# Dependency ordering
# ---------------------------------------------------------------------------


def test_three_level_dependency_chain_topological_order():
    """C -> B -> A: nodes should be ordered [C, B, A] (dependencies first)."""
    hippo = MagicMock()
    hippo.query_entities.return_value = []

    rule_c = _make_rule("make-c", "C")
    rule_b = _make_rule(
        "make-b",
        "B",
        requires=[{"bind": "c_in", "entity_type": "C", "resolve": "uri", "metadata": {}}],
    )
    rule_a = _make_rule(
        "make-a",
        "A",
        requires=[{"bind": "b_in", "entity_type": "B", "resolve": "uri", "metadata": {}}],
    )

    planner = _planner([rule_a, rule_b, rule_c], hippo)
    plan = planner.plan("A", {})

    task_names = [n.rule_name for n in plan.nodes if isinstance(n, CanonTask)]
    assert task_names.index("make-c") < task_names.index("make-b")
    assert task_names.index("make-b") < task_names.index("make-a")


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def test_cycle_detection_raises_canon_cycle_error():
    """A requires B, B requires A — must raise CanonCycleError."""
    hippo = MagicMock()
    hippo.query_entities.return_value = []

    rule_a = _make_rule(
        "make-a",
        "A",
        requires=[{"bind": "b_in", "entity_type": "B", "resolve": "uri", "metadata": {}}],
    )
    rule_b = _make_rule(
        "make-b",
        "B",
        requires=[{"bind": "a_in", "entity_type": "A", "resolve": "uri", "metadata": {}}],
    )

    planner = _planner([rule_a, rule_b], hippo)
    with pytest.raises(CanonCycleError):
        planner.plan("A", {})


# ---------------------------------------------------------------------------
# Diamond pattern
# ---------------------------------------------------------------------------


def test_diamond_no_false_cycle():
    """A requires B and C; B and C both require D — no false CanonCycleError."""
    hippo = MagicMock()
    hippo.query_entities.return_value = []

    rule_d = _make_rule("make-d", "D")
    rule_b = _make_rule(
        "make-b",
        "B",
        requires=[{"bind": "d_in", "entity_type": "D", "resolve": "uri", "metadata": {}}],
    )
    rule_c = _make_rule(
        "make-c",
        "C",
        requires=[{"bind": "d_in", "entity_type": "D", "resolve": "uri", "metadata": {}}],
    )
    rule_a = _make_rule(
        "make-a",
        "A",
        requires=[
            {"bind": "b_in", "entity_type": "B", "resolve": "uri", "metadata": {}},
            {"bind": "c_in", "entity_type": "C", "resolve": "uri", "metadata": {}},
        ],
    )

    planner = _planner([rule_a, rule_b, rule_c, rule_d], hippo)
    # Must not raise CanonCycleError
    plan = planner.plan("A", {})
    task_names = [n.rule_name for n in plan.nodes if isinstance(n, CanonTask)]
    assert "make-d" in task_names
    assert "make-a" in task_names
    assert task_names.index("make-d") < task_names.index("make-a")
