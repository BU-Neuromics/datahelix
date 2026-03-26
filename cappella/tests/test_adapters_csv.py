"""Tests for CSVAdapter."""
import pytest

from cappella.adapters.csv_adapter import CSVAdapter
from cappella.exceptions import AdapterFetchError, AdapterTransformError
from cappella.types import RawRecord, TransformedRecord


CSV_DATA = b"id,name,species\n1,Sample_A,human\n2,Sample_B,mouse\n"


def _make_adapter(**kwargs):
    config = {"entity_type": "sample", "external_id_field": "id", **kwargs}
    return CSVAdapter(config)


class TestCSVAdapterFetch:
    def test_manual_upload_yields_records(self):
        adapter = _make_adapter(source="manual_upload")
        records = list(adapter.fetch(data=CSV_DATA))
        assert len(records) == 2

    def test_records_have_correct_fields(self):
        adapter = _make_adapter(source="manual_upload")
        records = list(adapter.fetch(data=CSV_DATA))
        assert records[0].external_id == "1"
        assert records[0].data["name"] == "Sample_A"
        assert records[0].source_system == "csv"

    def test_missing_upload_data_raises(self):
        adapter = _make_adapter(source="manual_upload")
        with pytest.raises(AdapterFetchError, match="no upload data"):
            list(adapter.fetch())

    def test_unknown_source_raises(self):
        adapter = _make_adapter(source="ftp")
        with pytest.raises(AdapterFetchError, match="unknown source"):
            list(adapter.fetch())

    def test_file_source_missing_url_raises(self):
        adapter = _make_adapter(source="file")
        with pytest.raises(AdapterFetchError):
            list(adapter.fetch())

    def test_http_source_missing_url_raises(self):
        adapter = _make_adapter(source="http")
        with pytest.raises(AdapterFetchError):
            list(adapter.fetch())

    def test_file_source_reads_file(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_bytes(CSV_DATA)
        adapter = _make_adapter(source="file", url=str(f))
        records = list(adapter.fetch())
        assert len(records) == 2

    def test_name_default(self):
        adapter = _make_adapter(source="manual_upload")
        assert adapter.name == "csv"

    def test_custom_name(self):
        adapter = _make_adapter(source="manual_upload", name="my_lims")
        assert adapter.name == "my_lims"


class TestCSVAdapterTransform:
    def _fetch_one(self, data=CSV_DATA, **kwargs):
        adapter = _make_adapter(source="manual_upload", **kwargs)
        records = list(adapter.fetch(data=data))
        return adapter, records

    def test_transform_returns_transformed_record(self):
        adapter, records = self._fetch_one()
        t = adapter.transform(records[0])
        assert isinstance(t, TransformedRecord)

    def test_entity_type_set(self):
        adapter, records = self._fetch_one(entity_type="biospecimen")
        t = adapter.transform(records[0])
        assert t.entity_type == "biospecimen"

    def test_external_id_set(self):
        adapter, records = self._fetch_one()
        t = adapter.transform(records[0])
        assert t.external_id == "1"

    def test_field_map_applied(self):
        adapter, records = self._fetch_one(field_map={"name": "sample_name"})
        t = adapter.transform(records[0])
        assert "sample_name" in t.data
        assert "name" not in t.data

    def test_vocabulary_map_applied(self):
        adapter, records = self._fetch_one(
            vocabulary_map={"species": {"human": "Homo sapiens", "mouse": "Mus musculus"}}
        )
        t = adapter.transform(records[0])
        assert t.data["species"] == "Homo sapiens"

    def test_missing_external_id_raises(self):
        adapter = _make_adapter(source="manual_upload", external_id_field="missing_col")
        records = list(adapter.fetch(data=CSV_DATA))
        with pytest.raises(AdapterTransformError, match="missing_col"):
            adapter.transform(records[0])

    def test_trust_level_default(self):
        adapter, records = self._fetch_one()
        t = adapter.transform(records[0])
        assert t.trust_level == 50

    def test_trust_level_custom(self):
        adapter, records = self._fetch_one(trust_level=80)
        t = adapter.transform(records[0])
        assert t.trust_level == 80


class TestCSVAdapterHealthCheck:
    def test_manual_upload_health_ok(self):
        adapter = _make_adapter(source="manual_upload")
        result = adapter.health_check()
        assert result["status"] == "ok"

    def test_file_health_ok(self):
        adapter = _make_adapter(source="file", url="/tmp/foo.csv")
        result = adapter.health_check()
        assert result["status"] == "ok"
