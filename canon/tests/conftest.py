"""Shared test fixtures for Canon test suite."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from canon.types import Entity
from canon.rules.models import (
    ProductionRule,
    ProducesSpec,
    InputBinding,
    ExecuteSpec,
)


@pytest.fixture
def tmp_canon_yaml(tmp_path):
    """Create a minimal valid canon.yaml in tmp_path."""
    config_path = tmp_path / "canon.yaml"
    config_path.write_text(
        "hippo_url: http://localhost:8000\n"
        "hippo_token: testtoken\n"
        "executor: cwltool\n"
        "output_storage:\n"
        "  type: local\n"
        "  base_path: /tmp/canon-outputs\n"
    )
    return config_path


@pytest.fixture
def mock_hippo_client():
    """MagicMock hippo client with sensible defaults."""
    client = MagicMock()
    client.find_entity.return_value = None
    client.find_entities.return_value = []
    entity = Entity(
        id="test-uuid-1234",
        entity_type="AlignedReads",
        data={"uri": "/data/test.bam"},
    )
    client.ingest_entity.return_value = entity
    return client


@pytest.fixture
def sample_rule_data():
    """Dict representing a valid canon_rules.yaml rules list."""
    return {
        "rules": [
            {
                "name": "align-reads",
                "description": "Align reads with STAR",
                "produces": {
                    "entity_type": "AlignedReads",
                    "match": {
                        "sample": "{sample}",
                        "genome_build": "{genome_build}",
                    },
                },
                "requires": [
                    {
                        "bind": "reads",
                        "entity_type": "RawReads",
                        "match": {"sample": "{sample}"},
                    }
                ],
                "execute": {
                    "workflow": "workflows/star_align.cwl",
                    "inputs": {
                        "reads_fastq": "{reads.uri}",
                        "genome_build": "{genome_build}",
                    },
                },
            }
        ]
    }


@pytest.fixture
def sample_cwl_rule():
    """A ProductionRule with one requires and execute block."""
    return ProductionRule(
        name="align-reads",
        description="Align reads with STAR",
        produces=ProducesSpec(
            entity_type="AlignedReads",
            match={"sample": "{sample}", "genome_build": "{genome_build}"},
        ),
        requires=[
            InputBinding(
                bind="reads",
                entity_type="RawReads",
                match={"sample": "{sample}"},
            )
        ],
        execute=ExecuteSpec(
            workflow="workflows/star_align.cwl",
            inputs={
                "reads_fastq": "{reads.uri}",
                "genome_build": "{genome_build}",
            },
        ),
    )
