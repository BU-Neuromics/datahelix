"""Tests for CanonConfig loading and validation."""

from __future__ import annotations

import pytest
import yaml

from canon.config import CanonConfig
from canon.exceptions import CanonValidationError


def test_valid_config_loads(sample_config_yaml):
    config = CanonConfig.from_yaml(sample_config_yaml)
    assert config.hippo_url == "http://hippo.example.com"
    assert config.hippo_token == "test-token"
    assert config.executor == "local"
    assert config.rules_file == "canon_rules.yaml"
    assert config.work_dir == ".canon/work"


def test_missing_executor_raises(tmp_path):
    cfg = {"hippo_url": "http://hippo.example.com"}
    path = tmp_path / "canon.yaml"
    path.write_text(yaml.dump(cfg))
    with pytest.raises(CanonValidationError):
        CanonConfig.from_yaml(path)


def test_invalid_executor_raises(tmp_path):
    cfg = {"hippo_url": "http://hippo.example.com", "executor": "snakemake"}
    path = tmp_path / "canon.yaml"
    path.write_text(yaml.dump(cfg))
    with pytest.raises(CanonValidationError):
        CanonConfig.from_yaml(path)


def test_all_fields_accessible(sample_config_yaml):
    config = CanonConfig.from_yaml(sample_config_yaml)
    assert config.hippo_url
    assert config.executor
    assert config.rules_file
    assert config.work_dir
