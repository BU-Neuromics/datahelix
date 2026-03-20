"""Tests for LocalProcessExecutor."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from canon.config import CanonConfig
from canon.exceptions import CanonExecutorError
from canon.executors.base import ExecutorInputs, RunHandle, RunStatus
from canon.executors.local import LocalProcessExecutor
from canon.plan import CanonTask
from canon.rule_registry import RulesEngine
from canon.rules import ProductionRule
from canon.types import WildcardBinding


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config(tmp_path: Path) -> CanonConfig:
    return CanonConfig(
        hippo_url="http://hippo.example.com",
        executor="local",
        rules_file=str(tmp_path / "canon_rules.yaml"),
        work_dir=str(tmp_path / "work"),
    )


@pytest.fixture
def star_rule(sample_rule_dict: dict) -> ProductionRule:
    return ProductionRule.model_validate(sample_rule_dict)


@pytest.fixture
def engine(star_rule: ProductionRule) -> RulesEngine:
    return RulesEngine([star_rule])


@pytest.fixture
def sample_task(star_rule: ProductionRule) -> CanonTask:
    wb = WildcardBinding({"genome_build": "GRCh38", "sample_id": "S001"})
    return CanonTask(
        rule_name="align-with-star",
        wildcard_bindings=wb,
        input_entities={
            "raw_reads": {"uri": "file:///data/reads.fastq"},
            "genome_index": {"uri": "file:///data/GRCh38_index"},
        },
        output_spec=star_rule.execute.outputs,
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_render_returns_sh_workflow_path_and_inputs(config, engine, sample_task):
    executor = LocalProcessExecutor(config, engine)
    result = executor.render(sample_task)
    assert result.workflow_path.endswith(".sh")
    assert isinstance(result.inputs, dict)


def test_submit_launches_subprocess_and_returns_local_handle(
    config, engine, tmp_path
):
    script = tmp_path / "star_align.sh"
    script.write_text("#!/bin/bash\nsleep 30\n")
    script.chmod(0o755)

    executor = LocalProcessExecutor(config, engine)
    inputs = ExecutorInputs(workflow_path=str(script), inputs={})
    handle = executor.submit(inputs)

    assert handle.executor_type == "local"
    assert handle.run_id

    # Cleanup
    entry = executor._runs[handle.run_id]
    entry["proc"].terminate()
    entry["proc"].wait()


def test_poll_running_then_succeeded(config, engine, tmp_path):
    script = tmp_path / "fast.sh"
    script.write_text("#!/bin/bash\nexit 0\n")
    script.chmod(0o755)

    executor = LocalProcessExecutor(config, engine)
    inputs = ExecutorInputs(workflow_path=str(script), inputs={})
    handle = executor.submit(inputs)

    # Poll until done (fast script, max 5s)
    status = RunStatus.RUNNING
    for _ in range(100):
        status = executor.poll(handle)
        if status != RunStatus.RUNNING:
            break
        time.sleep(0.05)

    assert status == RunStatus.SUCCEEDED


def test_collect_outputs_returns_path_when_file_exists(config, engine, tmp_path):
    script = tmp_path / "fast.sh"
    script.write_text("#!/bin/bash\nexit 0\n")
    script.chmod(0o755)

    executor = LocalProcessExecutor(config, engine)
    inputs = ExecutorInputs(workflow_path=str(script), inputs={})
    handle = executor.submit(inputs)

    # Manually create the outputs file in the run's work_dir
    work_dir: Path = executor._runs[handle.run_id]["work_dir"]
    outputs_file = work_dir / ".canon_outputs.json"
    outputs_file.write_text('{"entities": []}')

    result = executor.collect_outputs(handle)
    assert result == outputs_file

    # Cleanup
    executor._runs[handle.run_id]["proc"].terminate()
    executor._runs[handle.run_id]["proc"].wait()


def test_collect_outputs_raises_if_canon_outputs_missing(config, engine, tmp_path):
    script = tmp_path / "fast.sh"
    script.write_text("#!/bin/bash\nexit 0\n")
    script.chmod(0o755)

    executor = LocalProcessExecutor(config, engine)
    inputs = ExecutorInputs(workflow_path=str(script), inputs={})
    handle = executor.submit(inputs)

    with pytest.raises(CanonExecutorError):
        executor.collect_outputs(handle)

    # Cleanup
    executor._runs[handle.run_id]["proc"].terminate()
    executor._runs[handle.run_id]["proc"].wait()


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_integration_real_subprocess_writes_outputs(config, engine, tmp_path):
    outputs_data = {
        "entities": [
            {"entity_type": "AlignmentFile", "data": {"uri": "file:///data/sample.bam"}}
        ]
    }
    script = tmp_path / "star_align.sh"
    script.write_text(
        "#!/bin/bash\n"
        'mkdir -p "$CANON_WORK_DIR"\n'
        f"echo '{json.dumps(outputs_data)}' > \"$CANON_WORK_DIR/.canon_outputs.json\"\n"
    )
    script.chmod(0o755)

    executor = LocalProcessExecutor(config, engine)
    inputs = ExecutorInputs(workflow_path=str(script), inputs={})
    handle = executor.submit(inputs)

    # Wait for completion (max 10s)
    status = RunStatus.RUNNING
    for _ in range(100):
        status = executor.poll(handle)
        if status != RunStatus.RUNNING:
            break
        time.sleep(0.1)

    assert status == RunStatus.SUCCEEDED
    outputs_path = executor.collect_outputs(handle)
    assert outputs_path.exists()
    data = json.loads(outputs_path.read_text())
    assert "entities" in data
