"""Tests for IngestPipeline."""
import pytest

from cappella.adapters.csv_adapter import CSVAdapter
from cappella.ingest.pipeline import IngestPipeline, IngestRunResult

CSV_DATA = b"id,name,species\n1,Sample_A,human\n2,Sample_B,mouse\n"
BAD_ID_DATA = b"no_id,name\nA,Alpha\n"  # missing the 'id' field


def _make_csv_adapter(**kwargs):
    config = {"entity_type": "sample", "external_id_field": "id", "source": "manual_upload", **kwargs}
    return CSVAdapter(config)


class TestIngestPipelineBasic:
    def test_returns_ingest_run_result(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=CSV_DATA)
        assert isinstance(result, IngestRunResult)

    def test_run_id_is_set(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=CSV_DATA)
        assert result.run_id

    def test_adapter_name_in_result(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter(name="my_lims")
        result = pipeline.run(adapter, data=CSV_DATA)
        assert result.adapter_name == "my_lims"

    def test_success_status_all_good(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=CSV_DATA)
        assert result.status == "success"

    def test_fetched_count(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=CSV_DATA)
        assert result.fetched == 2

    def test_transformed_count(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=CSV_DATA)
        assert result.transformed == 2

    def test_upserted_count(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=CSV_DATA)
        assert result.upserted == 2

    def test_duration_positive(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=CSV_DATA)
        assert result.duration_seconds >= 0


class TestIngestPipelinePartialFailure:
    def test_partial_success_on_transform_failure(self):
        pipeline = IngestPipeline()
        # Use 'id' field_map that doesn't rename, but external_id_field points to missing column
        adapter = _make_csv_adapter(external_id_field="missing_col")
        result = pipeline.run(adapter, data=CSV_DATA)
        # All records fetched, all transform-failed
        assert result.fetched == 2
        assert result.failed_transform == 2
        assert result.status in ("partial_success", "failed")

    def test_errors_list_populated_on_transform_failure(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter(external_id_field="missing_col")
        result = pipeline.run(adapter, data=CSV_DATA)
        assert len(result.errors) > 0


class TestIngestPipelineEmptyData:
    def test_empty_csv_gives_success(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        # Only header, no data rows
        result = pipeline.run(adapter, data=b"id,name,species\n")
        assert result.status == "success"
        assert result.fetched == 0

    def test_empty_pipeline_status_success(self):
        pipeline = IngestPipeline()
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter, data=b"id,name,species\n")
        assert result.upserted == 0


class TestIngestPipelineFetchFailure:
    def test_fetch_failure_returns_failed_status(self):
        pipeline = IngestPipeline()
        # No upload data provided for manual_upload → AdapterFetchError
        adapter = _make_csv_adapter()
        result = pipeline.run(adapter)  # no data kwarg → fetch error
        assert result.status == "failed"
        assert len(result.errors) > 0
