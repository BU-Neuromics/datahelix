"""Tests for JSONAdapter."""
import json

import pytest

from cappella.adapters.json_adapter import JSONAdapter
from cappella.exceptions import AdapterFetchError, AdapterTransformError
from cappella.types import RawRecord, TransformedRecord

RECORDS = [{"id": "s1", "name": "Alpha", "status": "active"}, {"id": "s2", "name": "Beta", "status": "inactive"}]
JSON_DATA = json.dumps(RECORDS).encode()
NESTED_DATA = json.dumps({"data": {"items": RECORDS}}).encode()


def _make_adapter(**kwargs):
    config = {"entity_type": "sample", "external_id_field": "id", **kwargs}
    return JSONAdapter(config)


class TestJSONAdapterFetch:
    def test_manual_upload_top_level_array(self):
        adapter = _make_adapter(source="manual_upload", records_path="$[*]")
        records = list(adapter.fetch(data=JSON_DATA))
        assert len(records) == 2

    def test_records_have_correct_fields(self):
        adapter = _make_adapter(source="manual_upload", records_path="$[*]")
        records = list(adapter.fetch(data=JSON_DATA))
        assert records[0].external_id == "s1"
        assert records[0].data["name"] == "Alpha"

    def test_nested_jsonpath(self):
        adapter = _make_adapter(source="manual_upload", records_path="$.data.items[*]")
        records = list(adapter.fetch(data=NESTED_DATA))
        assert len(records) == 2

    def test_missing_upload_data_raises(self):
        adapter = _make_adapter(source="manual_upload")
        with pytest.raises(AdapterFetchError, match="no upload data"):
            list(adapter.fetch())

    def test_unknown_source_raises(self):
        adapter = _make_adapter(source="ftp")
        with pytest.raises(AdapterFetchError, match="unknown source"):
            list(adapter.fetch())

    def test_invalid_json_raises(self):
        adapter = _make_adapter(source="manual_upload")
        with pytest.raises(AdapterFetchError, match="malformed JSON"):
            list(adapter.fetch(data=b"not json"))

    def test_file_source(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_bytes(JSON_DATA)
        adapter = _make_adapter(source="file", url=str(f), records_path="$[*]")
        records = list(adapter.fetch())
        assert len(records) == 2

    def test_name_default(self):
        adapter = _make_adapter(source="manual_upload")
        assert adapter.name == "json"


class TestJSONAdapterTransform:
    def _fetch_one(self, data=JSON_DATA, **kwargs):
        adapter = _make_adapter(source="manual_upload", records_path="$[*]", **kwargs)
        records = list(adapter.fetch(data=data))
        return adapter, records

    def test_transform_returns_transformed_record(self):
        adapter, records = self._fetch_one()
        t = adapter.transform(records[0])
        assert isinstance(t, TransformedRecord)

    def test_external_id_set(self):
        adapter, records = self._fetch_one()
        t = adapter.transform(records[0])
        assert t.external_id == "s1"

    def test_field_map_applied(self):
        adapter, records = self._fetch_one(field_map={"name": "sample_name"})
        t = adapter.transform(records[0])
        assert "sample_name" in t.data
        assert "name" not in t.data

    def test_vocabulary_map_applied(self):
        adapter, records = self._fetch_one(
            vocabulary_map={"status": {"active": "ACTIVE", "inactive": "INACTIVE"}}
        )
        t = adapter.transform(records[0])
        assert t.data["status"] == "ACTIVE"

    def test_missing_external_id_raises(self):
        adapter = _make_adapter(source="manual_upload", records_path="$[*]", external_id_field="no_field")
        records = list(adapter.fetch(data=JSON_DATA))
        with pytest.raises(AdapterTransformError, match="no_field"):
            adapter.transform(records[0])

    def test_trust_level(self):
        adapter, records = self._fetch_one(trust_level=75)
        t = adapter.transform(records[0])
        assert t.trust_level == 75
