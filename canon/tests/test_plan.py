"""Tests for execution plan types."""

from __future__ import annotations

import pytest

from canon.executors.base import ExecutorInputs, RunHandle, RunStatus
from canon.plan import CanonTask, EntityRef, ExecutionPlan, NodeDecision
from canon.rules import OutputSpec
from canon.types import WildcardBinding


# ---------------------------------------------------------------------------
# EntityRef
# ---------------------------------------------------------------------------


def test_entity_ref_has_correct_fields_and_reuse_decision():
    ref = EntityRef(
        entity_id="e-1",
        entity_type="AlignmentFile",
        metadata={"aligner": "STAR"},
    )
    assert ref.entity_id == "e-1"
    assert ref.entity_type == "AlignmentFile"
    assert ref.metadata == {"aligner": "STAR"}
    assert ref.decision == NodeDecision.REUSE


# ---------------------------------------------------------------------------
# CanonTask
# ---------------------------------------------------------------------------


def test_canon_task_has_correct_fields_and_build_decision():
    wb = WildcardBinding({"sample_id": "S001", "genome_build": "GRCh38"})
    output = OutputSpec(bind="bam", entity_type="AlignmentFile", pattern="S001.bam")
    task = CanonTask(
        rule_name="align-with-star",
        wildcard_bindings=wb,
        input_entities={"raw_reads": {"uri": "file:///x.fastq"}},
        output_spec=[output],
    )
    assert task.rule_name == "align-with-star"
    assert task.wildcard_bindings["sample_id"] == "S001"
    assert task.decision == NodeDecision.BUILD


# ---------------------------------------------------------------------------
# ExecutionPlan serialisation round-trip
# ---------------------------------------------------------------------------


def _make_plan() -> ExecutionPlan:
    wb = WildcardBinding({"sample_id": "S001", "genome_build": "GRCh38"})
    output = OutputSpec(bind="bam", entity_type="AlignmentFile", pattern="{sample_id}.bam")
    task = CanonTask(
        rule_name="align-with-star",
        wildcard_bindings=wb,
        input_entities={},
        output_spec=[output],
    )
    ref = EntityRef(
        entity_id="e-1",
        entity_type="GenomeIndex",
        metadata={"genome_build": "GRCh38"},
    )
    return ExecutionPlan(nodes=[ref, task])


def test_execution_plan_to_json_from_json_roundtrip():
    plan = _make_plan()
    json_str = plan.to_json()
    restored = ExecutionPlan.from_json(json_str)
    assert len(restored.nodes) == 2
    assert isinstance(restored.nodes[0], EntityRef)
    assert isinstance(restored.nodes[1], CanonTask)
    assert restored.nodes[1].rule_name == "align-with-star"
    assert restored.nodes[1].wildcard_bindings["sample_id"] == "S001"


def test_execution_plan_build_nodes_returns_only_tasks():
    plan = _make_plan()
    build = plan.build_nodes
    assert len(build) == 1
    assert all(isinstance(n, CanonTask) for n in build)


def test_execution_plan_reuse_nodes_returns_only_refs():
    plan = _make_plan()
    reuse = plan.reuse_nodes
    assert len(reuse) == 1
    assert all(isinstance(n, EntityRef) for n in reuse)


# ---------------------------------------------------------------------------
# RunHandle, RunStatus, ExecutorInputs
# ---------------------------------------------------------------------------


def test_run_handle_fields():
    handle = RunHandle(run_id="run-123", executor_type="local", meta={"key": "val"})
    assert handle.run_id == "run-123"
    assert handle.executor_type == "local"
    assert handle.meta == {"key": "val"}


def test_run_status_values():
    assert RunStatus.PENDING == "PENDING"
    assert RunStatus.RUNNING == "RUNNING"
    assert RunStatus.SUCCEEDED == "SUCCEEDED"
    assert RunStatus.FAILED == "FAILED"


def test_executor_inputs_fields():
    inputs = ExecutorInputs(workflow_path="/path/to/script.sh", inputs={"KEY": "value"})
    assert inputs.workflow_path == "/path/to/script.sh"
    assert inputs.inputs == {"KEY": "value"}
