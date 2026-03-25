"""Tests for CwltoolAdapter."""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch

from canon.executors.cwltool import CwltoolAdapter
from canon.config import CanonConfig
from canon.exceptions import CanonConfigError


def _make_adapter(cwltool_options=None):
    config = MagicMock(spec=CanonConfig)
    config.cwltool_options = cwltool_options or []
    return CwltoolAdapter(config)


# ---------------------------------------------------------------------------
# validate_available
# ---------------------------------------------------------------------------

def test_validate_available_passes_when_cwltool_on_path():
    with patch("canon.executors.cwltool.shutil.which", return_value="/usr/bin/cwltool"):
        adapter = _make_adapter()
        adapter.validate_available()  # must not raise


def test_validate_available_raises_when_cwltool_missing():
    with patch("canon.executors.cwltool.shutil.which", return_value=None):
        adapter = _make_adapter()
        with pytest.raises(CanonConfigError, match="cwltool not found"):
            adapter.validate_available()


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def test_run_writes_inputs_json(tmp_path):
    adapter = _make_adapter()
    inputs = {"sample": "S001", "genome": "GRCh38"}

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps({"output_bam": {"location": "/tmp/out.bam"}})
    mock_proc.stderr = ""

    with patch("canon.executors.cwltool.subprocess.run", return_value=mock_proc):
        adapter.run("workflow.cwl", inputs, str(tmp_path))

    inputs_file = tmp_path / "inputs.json"
    assert inputs_file.exists()
    assert json.loads(inputs_file.read_text()) == inputs


def test_run_parses_json_stdout(tmp_path):
    adapter = _make_adapter()
    outputs_dict = {"output_bam": {"location": "/tmp/out.bam", "class": "File"}}

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps(outputs_dict)
    mock_proc.stderr = ""

    with patch("canon.executors.cwltool.subprocess.run", return_value=mock_proc):
        result = adapter.run("workflow.cwl", {}, str(tmp_path))

    assert result.exit_code == 0
    assert result.outputs == outputs_dict


def test_run_returns_nonzero_exit_code(tmp_path):
    adapter = _make_adapter()

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "Something went wrong"

    with patch("canon.executors.cwltool.subprocess.run", return_value=mock_proc):
        result = adapter.run("workflow.cwl", {}, str(tmp_path))

    assert result.exit_code == 1
    assert result.stderr == "Something went wrong"


def test_run_calls_subprocess_with_cwl_path(tmp_path):
    adapter = _make_adapter(cwltool_options=["--no-container"])

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "{}"
    mock_proc.stderr = ""

    with patch("canon.executors.cwltool.subprocess.run", return_value=mock_proc) as mock_run:
        adapter.run("my/workflow.cwl", {}, str(tmp_path))

    call_args = mock_run.call_args[0][0]  # first positional arg (the cmd list)
    assert "cwltool" in call_args[0]
    assert "--no-container" in call_args
    assert "my/workflow.cwl" in call_args


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

def test_version_parses_cwltool_format():
    mock_proc = MagicMock()
    mock_proc.stdout = "cwltool 3.1.20240112164112"
    mock_proc.stderr = ""

    with patch("canon.executors.cwltool.subprocess.run", return_value=mock_proc):
        adapter = _make_adapter()
        version = adapter.version()

    assert "cwltool" in version
    assert "3.1" in version


# ---------------------------------------------------------------------------
# Executor storage flags
# ---------------------------------------------------------------------------

def test_cwltool_adapter_requires_local_staging():
    adapter = _make_adapter()
    assert adapter.requires_local_staging is True


def test_cwltool_adapter_requires_output_relocation():
    adapter = _make_adapter()
    assert adapter.requires_output_relocation is True


def test_cwltool_adapter_inherits_flags_from_abc():
    from canon.executors.base import CWLExecutorAdapter
    assert CWLExecutorAdapter.requires_local_staging is True
    assert CWLExecutorAdapter.requires_output_relocation is True
