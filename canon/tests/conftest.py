"""Shared fixtures for Canon test suite."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from canon.hippo_client import HippoClient


@pytest.fixture
def sample_rule_dict() -> dict:
    """The STAR alignment rule from the Canon design notes."""
    return {
        "name": "align-with-star",
        "produces": {
            "entity_type": "AlignmentFile",
            "metadata": {
                "aligner": "STAR",
                "genome_build": "{genome_build}",
                "sample_id": "{sample_id}",
            },
        },
        "requires": [
            {
                "bind": "raw_reads",
                "entity_type": "RawReads",
                "resolve": "uri",
                "metadata": {"sample_id": "{sample_id}"},
            },
            {
                "bind": "genome_index",
                "entity_type": "GenomeIndex",
                "resolve": "uri",
                "metadata": {"genome_build": "{genome_build}"},
            },
        ],
        "execute": {
            "workflow": "star_align",
            "inputs": {
                "READS": "{raw_reads}",
                "GENOME_DIR": "{genome_index}",
                "SAMPLE_ID": "{sample_id}",
            },
            "outputs": [
                {
                    "bind": "bam",
                    "entity_type": "AlignmentFile",
                    "pattern": "{sample_id}.bam",
                }
            ],
        },
    }


@pytest.fixture
def sample_rules_yaml(tmp_path: Path, sample_rule_dict: dict) -> Path:
    """Write a canon_rules.yaml with 3 rules to tmp_path."""
    rules = [
        sample_rule_dict,
        {
            "name": "index-genome",
            "produces": {
                "entity_type": "GenomeIndex",
                "metadata": {"genome_build": "{genome_build}"},
            },
            "requires": [],
            "execute": {
                "workflow": "star_index",
                "inputs": {"GENOME_BUILD": "{genome_build}"},
                "outputs": [
                    {
                        "bind": "index",
                        "entity_type": "GenomeIndex",
                        "pattern": "{genome_build}_index/",
                    }
                ],
            },
        },
        {
            "name": "qc-reads",
            "produces": {
                "entity_type": "QCReport",
                "metadata": {"sample_id": "{sample_id}"},
            },
            "requires": [],
            "execute": {
                "workflow": "fastqc",
                "inputs": {"SAMPLE_ID": "{sample_id}"},
                "outputs": [
                    {
                        "bind": "report",
                        "entity_type": "QCReport",
                        "pattern": "{sample_id}_qc.html",
                    }
                ],
            },
        },
    ]
    path = tmp_path / "canon_rules.yaml"
    path.write_text(yaml.dump(rules))
    return path


@pytest.fixture
def sample_config_yaml(tmp_path: Path) -> Path:
    """Write a canon.yaml to tmp_path."""
    config = {
        "hippo_url": "http://hippo.example.com",
        "hippo_token": "test-token",
        "executor": "local",
        "rules_file": "canon_rules.yaml",
        "work_dir": ".canon/work",
    }
    path = tmp_path / "canon.yaml"
    path.write_text(yaml.dump(config))
    return path


@pytest.fixture
def sample_entity_dict() -> dict:
    """A sample AlignmentFile entity as returned by Hippo."""
    return {
        "id": "ent-001",
        "entity_type": "AlignmentFile",
        "data": {
            "aligner": "STAR",
            "genome_build": "GRCh38",
            "sample_id": "S001",
            "uri": "file:///data/sample.bam",
        },
    }


@pytest.fixture
def mock_hippo_client(monkeypatch) -> MagicMock:
    """Return a Mock HippoClient."""
    mock = MagicMock(spec=HippoClient)
    return mock
