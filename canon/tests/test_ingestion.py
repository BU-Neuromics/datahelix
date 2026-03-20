"""Tests for OutputIngestionPipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from canon.exceptions import CanonIngestionError
from canon.hippo_client import HippoClient
from canon.ingestion import OutputIngestionPipeline


def _write_outputs(work_dir: Path, data: object) -> None:
    (work_dir / ".canon_outputs.json").write_text(json.dumps(data))


def test_valid_ingest_returns_entity_ids(tmp_path):
    mock_hippo = MagicMock(spec=HippoClient)
    mock_hippo.ingest_entities.return_value = ["ent-001"]
    data = {
        "entities": [
            {"entity_type": "AlignmentFile", "data": {"uri": "file:///x.bam"}}
        ]
    }
    _write_outputs(tmp_path, data)
    pipeline = OutputIngestionPipeline(mock_hippo)
    ids = pipeline.ingest(tmp_path)
    assert ids == ["ent-001"]
    mock_hippo.ingest_entities.assert_called_once()


def test_missing_entities_key_raises_before_http(tmp_path):
    mock_hippo = MagicMock(spec=HippoClient)
    _write_outputs(tmp_path, {"results": []})
    pipeline = OutputIngestionPipeline(mock_hippo)
    with pytest.raises(CanonIngestionError):
        pipeline.ingest(tmp_path)
    mock_hippo.ingest_entities.assert_not_called()


def test_missing_entity_type_raises_before_http(tmp_path):
    mock_hippo = MagicMock(spec=HippoClient)
    data = {"entities": [{"data": {"uri": "file:///x.bam"}}]}
    _write_outputs(tmp_path, data)
    pipeline = OutputIngestionPipeline(mock_hippo)
    with pytest.raises(CanonIngestionError):
        pipeline.ingest(tmp_path)
    mock_hippo.ingest_entities.assert_not_called()


def test_missing_data_raises_before_http(tmp_path):
    mock_hippo = MagicMock(spec=HippoClient)
    data = {"entities": [{"entity_type": "AlignmentFile"}]}
    _write_outputs(tmp_path, data)
    pipeline = OutputIngestionPipeline(mock_hippo)
    with pytest.raises(CanonIngestionError):
        pipeline.ingest(tmp_path)
    mock_hippo.ingest_entities.assert_not_called()


def test_hippo_4xx_raises_canon_ingestion_error_with_status_code(tmp_path):
    mock_hippo = MagicMock(spec=HippoClient)
    mock_hippo.ingest_entities.side_effect = CanonIngestionError(
        "Hippo batch ingest failed (400): bad request"
    )
    data = {
        "entities": [
            {"entity_type": "AlignmentFile", "data": {"uri": "file:///x.bam"}}
        ]
    }
    _write_outputs(tmp_path, data)
    pipeline = OutputIngestionPipeline(mock_hippo)
    with pytest.raises(CanonIngestionError, match="400"):
        pipeline.ingest(tmp_path)
