"""Tests for SQLAdapter, including query safety and SQLite integration."""
import pytest

from cappella.adapters.sql_adapter import SQLAdapter, _check_query_safety
from cappella.exceptions import AdapterFetchError, AdapterTransformError, ConfigError
from cappella.types import TransformedRecord


def _make_adapter(**kwargs):
    config = {
        "entity_type": "sample",
        "external_id_field": "id",
        "connection_string": "sqlite:///:memory:",
        "query": "SELECT 1 AS id, 'test' AS name",
        **kwargs,
    }
    return SQLAdapter(config)


class TestQuerySafety:
    @pytest.mark.parametrize("keyword", ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "EXEC"])
    def test_forbidden_keyword_raises(self, keyword):
        with pytest.raises(ConfigError, match=keyword):
            _check_query_safety(f"{keyword} INTO foo VALUES (1)")

    def test_select_is_allowed(self):
        _check_query_safety("SELECT id, name FROM samples WHERE active = 1")

    def test_select_with_subquery_is_allowed(self):
        _check_query_safety("SELECT * FROM (SELECT id FROM foo) AS sub")

    def test_case_insensitive_detection(self):
        with pytest.raises(ConfigError, match="DELETE"):
            _check_query_safety("delete from foo")

    def test_word_boundary_not_triggered_by_substring(self):
        # "EXECUTION" contains "EXEC" but as a substring — depends on word boundary
        # The implementation uses \bEXEC\b so "EXECUTION" should NOT trigger
        _check_query_safety("SELECT execution_plan FROM foo")


class TestSQLAdapterInit:
    def test_forbidden_query_raises_at_init(self):
        with pytest.raises(ConfigError):
            SQLAdapter({
                "connection_string": "sqlite:///:memory:",
                "query": "DROP TABLE samples",
                "entity_type": "sample",
                "external_id_field": "id",
            })

    def test_forbidden_incremental_query_raises_at_init(self):
        with pytest.raises(ConfigError):
            SQLAdapter({
                "connection_string": "sqlite:///:memory:",
                "query": "SELECT 1 AS id",
                "incremental_query": "DELETE FROM foo",
                "entity_type": "sample",
                "external_id_field": "id",
            })

    def test_supports_incremental_true(self):
        adapter = _make_adapter()
        assert adapter.supports_incremental is True

    def test_name_default(self):
        adapter = _make_adapter()
        assert adapter.name == "sql"


class TestSQLAdapterFetchAndTransform:
    def test_fetch_yields_records(self):
        adapter = _make_adapter(query="SELECT '42' AS id, 'Foo' AS name")
        records = list(adapter.fetch())
        assert len(records) == 1
        assert records[0].external_id == "42"
        assert records[0].data["name"] == "Foo"

    def test_transform_basic(self):
        adapter = _make_adapter(query="SELECT '42' AS id, 'Foo' AS name")
        records = list(adapter.fetch())
        t = adapter.transform(records[0])
        assert isinstance(t, TransformedRecord)
        assert t.external_id == "42"
        assert t.entity_type == "sample"

    def test_transform_field_map(self):
        adapter = _make_adapter(
            query="SELECT '1' AS id, 'Alpha' AS raw_name",
            field_map={"raw_name": "sample_name"},
        )
        records = list(adapter.fetch())
        t = adapter.transform(records[0])
        assert "sample_name" in t.data
        assert "raw_name" not in t.data

    def test_transform_vocabulary_map(self):
        adapter = _make_adapter(
            query="SELECT '1' AS id, 'human' AS species",
            vocabulary_map={"species": {"human": "Homo sapiens"}},
        )
        records = list(adapter.fetch())
        t = adapter.transform(records[0])
        assert t.data["species"] == "Homo sapiens"

    def test_transform_missing_external_id_raises(self):
        adapter = _make_adapter(
            query="SELECT 'X' AS name",
            external_id_field="id",
        )
        records = list(adapter.fetch())
        with pytest.raises(AdapterTransformError, match="id"):
            adapter.transform(records[0])

    def test_bad_connection_raises_fetch_error(self):
        adapter = SQLAdapter({
            "connection_string": "postgresql://invalid:bad@localhost:1/nodb",
            "query": "SELECT 1 AS id",
            "entity_type": "sample",
            "external_id_field": "id",
        })
        with pytest.raises(AdapterFetchError):
            list(adapter.fetch())

    def test_trust_level_on_transform(self):
        adapter = _make_adapter(
            query="SELECT '1' AS id, 'Foo' AS name",
            trust_level=90,
        )
        records = list(adapter.fetch())
        t = adapter.transform(records[0])
        assert t.trust_level == 90
