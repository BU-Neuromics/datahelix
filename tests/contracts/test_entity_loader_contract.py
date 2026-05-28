"""Contract tests: EntityLoader behavioral contracts.

These tests document the behavioral guarantees of the unified ingestion loader
framework introduced in platform/design/sec4_unified_ingestion.md.

They cover:
- EntityLoader ABC enforcement
- ConfigurableLoader field/vocab mapping
- CSVLoader fetch + transform
- IngestPipeline create / unchanged / update cycle, partial failure, and dry_run

Run with: PYTHONPATH=hippo/src:canon/src uv run pytest tests/contracts/test_entity_loader_contract.py -v --tb=short
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterator

import pytest

_root = Path(__file__).parent.parent.parent
for _pkg in ("hippo/src", "canon/src"):
    _p = str(_root / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hippo.core.client import HippoClient
from hippo.core.exceptions import EntityNotFoundError
from hippo.core.loaders.base import ConfigurableLoader, EntityLoader, RawRecord
from hippo.core.loaders.csv import CSVLoader
from hippo.core.loaders.pipeline import IngestPipeline
from hippo.core.storage.adapters.sqlite_adapter import SQLiteAdapter

from tests.conftest import build_test_schema_registry


def _make_client(tmp_path: Path) -> HippoClient:
    registry = build_test_schema_registry()
    storage = SQLiteAdapter(str(tmp_path / "hippo.db"), schema_registry=registry)
    return HippoClient(storage=storage, registry=registry)


# ---------------------------------------------------------------------------
# CONTRACT: EntityLoader ABC
# ---------------------------------------------------------------------------


class _ConcreteLoader(ConfigurableLoader):
    """Minimal concrete ConfigurableLoader for testing transform() in isolation."""

    def fetch(self, since=None, **kwargs) -> Iterator[RawRecord]:
        return iter([])


class TestEntityLoaderContract:
    """EntityLoader must enforce the fetch/transform interface on all subclasses."""

    def test_entity_loader_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            EntityLoader()  # type: ignore[abstract]

    def test_subclass_missing_fetch_cannot_be_instantiated(self):
        class NoFetch(EntityLoader):
            def transform(self, record: RawRecord) -> dict:
                return record

        with pytest.raises(TypeError):
            NoFetch()  # type: ignore[abstract]

    def test_subclass_missing_transform_cannot_be_instantiated(self):
        class NoTransform(EntityLoader):
            def fetch(self, since=None, **kwargs) -> Iterator[RawRecord]:
                return iter([])

        with pytest.raises(TypeError):
            NoTransform()  # type: ignore[abstract]

    def test_configurable_loader_transform_applies_field_map(self):
        loader = _ConcreteLoader(
            {"entity_type": "sample", "field_map": {"src_name": "name"}}
        )
        result = loader.transform({"src_name": "Alpha", "id": "1"})
        assert "name" in result
        assert "src_name" not in result
        assert result["name"] == "Alpha"

    def test_configurable_loader_transform_applies_vocabulary_map(self):
        loader = _ConcreteLoader(
            {
                "entity_type": "sample",
                "vocabulary_map": {"species": {"human": "Homo sapiens"}},
            }
        )
        result = loader.transform({"id": "1", "species": "human"})
        assert result["species"] == "Homo sapiens"

    def test_configurable_loader_transform_preserves_unmapped_fields(self):
        loader = _ConcreteLoader(
            {"entity_type": "sample", "field_map": {"old": "new"}}
        )
        result = loader.transform({"old": "X", "extra": "keep_me", "num": 42})
        assert "extra" in result
        assert result["extra"] == "keep_me"
        assert result["num"] == 42


# ---------------------------------------------------------------------------
# CONTRACT: CSVLoader
# ---------------------------------------------------------------------------


class TestCSVLoaderContract:
    """CSVLoader must produce plain dicts from CSV bytes or files."""

    _CSV = b"id,name,species\n1,Alpha,human\n2,Beta,mouse\n"

    def test_fetch_from_bytes_yields_dicts(self):
        loader = CSVLoader({"entity_type": "sample", "external_id_field": "id"})
        records = list(loader.fetch(data=self._CSV))
        assert len(records) == 2
        assert all(isinstance(r, dict) for r in records)

    def test_fetch_from_bytes_has_correct_fields(self):
        loader = CSVLoader({"entity_type": "sample", "external_id_field": "id"})
        records = list(loader.fetch(data=self._CSV))
        assert records[0]["id"] == "1"
        assert records[0]["name"] == "Alpha"
        assert records[1]["id"] == "2"

    def test_fetch_from_file_yields_same_records(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_bytes(self._CSV)
        loader = CSVLoader(
            {
                "entity_type": "sample",
                "external_id_field": "id",
                "source_file": str(f),
            }
        )
        records = list(loader.fetch())
        assert len(records) == 2
        assert records[0]["id"] == "1"

    def test_transform_produces_dict_with_loader_entity_type(self):
        loader = CSVLoader(
            {
                "entity_type": "biospecimen",
                "external_id_field": "id",
                "field_map": {"name": "sample_name"},
            }
        )
        record = {"id": "1", "name": "Alpha"}
        result = loader.transform(record)
        assert isinstance(result, dict)
        assert loader.entity_type == "biospecimen"
        assert "sample_name" in result
        assert "name" not in result

    def test_fetch_raises_on_missing_file(self):
        loader = CSVLoader(
            {
                "entity_type": "sample",
                "source_file": "/nonexistent/path/does_not_exist.csv",
            }
        )
        with pytest.raises((FileNotFoundError, OSError)):
            list(loader.fetch())

    def test_fetch_raises_when_no_source_configured(self):
        loader = CSVLoader({"entity_type": "sample"})
        with pytest.raises(ValueError, match="no source"):
            list(loader.fetch())


# ---------------------------------------------------------------------------
# CONTRACT: IngestPipeline (create / unchanged / update cycle)
# ---------------------------------------------------------------------------


class TestIngestPipelineContract:
    """IngestPipeline must produce correct created/unchanged/updated counts.

    Uses a real HippoClient backed by SQLite so the idempotency logic is
    exercised end-to-end, not mocked away.
    """

    _CSV_V1 = b"id,name\n1,Alpha\n"
    _CSV_V2 = b"id,name\n1,Beta\n"
    # Two rows: first has id="fail" (will raise in PartialLoader), second is good
    _CSV_MIXED = b"id,name\nfail,Alpha\n1,Beta\n"

    def _make_loader(self, **kwargs) -> CSVLoader:
        config = {"entity_type": "Sample", "external_id_field": "id", **kwargs}
        return CSVLoader(config)

    def test_first_run_creates_entity(self, tmp_path):
        loader = self._make_loader()
        client = _make_client(tmp_path)
        pipeline = IngestPipeline(client, loader)
        result = pipeline.run(data=self._CSV_V1)
        assert result.created == 1
        assert result.total_rows == 1
        assert result.errors == 0

    def test_second_run_with_same_data_is_unchanged(self, tmp_path):
        loader = self._make_loader()
        client = _make_client(tmp_path)
        pipeline = IngestPipeline(client, loader)
        pipeline.run(data=self._CSV_V1)
        result2 = pipeline.run(data=self._CSV_V1)
        assert result2.unchanged == 1
        assert result2.created == 0
        assert result2.updated == 0

    def test_third_run_with_changed_data_updates_entity(self, tmp_path):
        loader = self._make_loader()
        client = _make_client(tmp_path)
        pipeline = IngestPipeline(client, loader)
        pipeline.run(data=self._CSV_V1)
        pipeline.run(data=self._CSV_V1)
        result3 = pipeline.run(data=self._CSV_V2)
        assert result3.updated == 1
        assert result3.created == 0

    def test_partial_failure_does_not_abort_pipeline(self, tmp_path):
        """Records that raise in transform() are counted as errors;
        remaining records are still processed."""

        class PartialLoader(CSVLoader):
            def transform(self, record: RawRecord) -> dict:
                if record.get("id") == "fail":
                    raise ValueError("intentional transform failure")
                return super().transform(record)

        loader = PartialLoader(
            {"entity_type": "Sample", "external_id_field": "id"}
        )
        client = _make_client(tmp_path)
        pipeline = IngestPipeline(client, loader)
        result = pipeline.run(data=self._CSV_MIXED)

        assert result.total_rows == 2
        assert result.errors == 1
        assert result.created == 1  # "1,Beta" was processed successfully
        assert len(result.error_messages) >= 1

    def test_dry_run_counts_records_without_writing(self, tmp_path):
        loader = self._make_loader()
        client = _make_client(tmp_path)
        pipeline = IngestPipeline(client, loader)

        result = pipeline.run(data=self._CSV_V1, dry_run=True)

        assert result.created == 1
        # Nothing was written to storage
        with pytest.raises(EntityNotFoundError):
            client.get_by_external_id("1")
