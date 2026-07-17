"""Tests for CanonConfig.load()."""

from __future__ import annotations

import pytest

from canon.config import CanonConfig
from canon.exceptions import CanonConfigError


def _write(tmp_path, content: str):
    p = tmp_path / "canon.yaml"
    p.write_text(content)
    return p


def test_valid_config_loads(tmp_canon_yaml):
    config = CanonConfig.load(tmp_canon_yaml)
    assert config.mosaic_url == "http://localhost:8000"
    assert config.mosaic_token == "testtoken"
    assert config.executor == "cwltool"
    assert config.output_storage.type == "local"
    assert config.output_storage.base_path == "/tmp/canon-outputs"


def test_missing_mosaic_url_raises(tmp_path):
    p = _write(
        tmp_path,
        "mosaic_token: tok\nexecutor: cwltool\noutput_storage:\n  type: local\n  base_path: /x\n",
    )
    with pytest.raises(CanonConfigError, match="mosaic_url"):
        CanonConfig.load(p)


def test_missing_mosaic_token_raises(tmp_path):
    p = _write(
        tmp_path,
        "mosaic_url: http://localhost:8000\nexecutor: cwltool\noutput_storage:\n  type: local\n  base_path: /x\n",
    )
    with pytest.raises(CanonConfigError, match="mosaic_token"):
        CanonConfig.load(p)


def test_invalid_log_level_raises(tmp_path):
    p = _write(
        tmp_path,
        (
            "mosaic_url: http://localhost:8000\n"
            "mosaic_token: tok\n"
            "executor: cwltool\n"
            "log_level: VERBOSE\n"
            "output_storage:\n  type: local\n  base_path: /x\n"
        ),
    )
    with pytest.raises(CanonConfigError, match="log_level"):
        CanonConfig.load(p)


def test_missing_output_storage_raises(tmp_path):
    p = _write(
        tmp_path,
        "mosaic_url: http://localhost:8000\nmosaic_token: tok\nexecutor: cwltool\n",
    )
    with pytest.raises(CanonConfigError, match="output_storage"):
        CanonConfig.load(p)


def test_env_var_substitution(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_MOSAIC_TOKEN", "secrettoken")
    p = _write(
        tmp_path,
        (
            "mosaic_url: http://localhost:8000\n"
            "mosaic_token: ${MY_MOSAIC_TOKEN}\n"
            "executor: cwltool\n"
            "output_storage:\n  type: local\n  base_path: /x\n"
        ),
    )
    config = CanonConfig.load(p)
    assert config.mosaic_token == "secrettoken"


def test_missing_env_var_raises(tmp_path):
    p = _write(
        tmp_path,
        (
            "mosaic_url: http://localhost:8000\n"
            "mosaic_token: ${CANON_TEST_MISSING_VAR_XYZ}\n"
            "executor: cwltool\n"
            "output_storage:\n  type: local\n  base_path: /x\n"
        ),
    )
    with pytest.raises(CanonConfigError, match="CANON_TEST_MISSING_VAR_XYZ"):
        CanonConfig.load(p)


def test_invalid_yaml_raises(tmp_path):
    p = _write(tmp_path, "{\ninvalid: yaml: [\n")
    with pytest.raises(CanonConfigError):
        CanonConfig.load(p)


def test_unknown_fields_ignored(tmp_path):
    p = _write(
        tmp_path,
        (
            "mosaic_url: http://localhost:8000\n"
            "mosaic_token: tok\n"
            "executor: cwltool\n"
            "output_storage:\n  type: local\n  base_path: /x\n"
            "totally_unknown_field: some_value\n"
            "another_unknown: 123\n"
        ),
    )
    # Pydantic extra='ignore' — must not raise
    config = CanonConfig.load(p)
    assert config.mosaic_url == "http://localhost:8000"
