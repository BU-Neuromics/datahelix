"""Unit tests for output formatters."""

from __future__ import annotations

import csv
import io
import json

import pytest

from aperture.cli.display.formatters import auto_columns, format_output
from aperture.models.display import ColumnDef, DisplayResult, OutputFormat


# --- JSON formatter ---


class TestJsonFormatter:
    def test_json_list(self) -> None:
        data = [{"id": "1", "name": "Sample A"}, {"id": "2", "name": "Sample B"}]
        result = DisplayResult(data=data)
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.JSON, file=buf)
        parsed = json.loads(buf.getvalue())
        assert parsed == data

    def test_json_detail(self) -> None:
        data = {"id": "1", "name": "Sample A", "status": "active"}
        result = DisplayResult(data=data, is_detail=True)
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.JSON, file=buf)
        parsed = json.loads(buf.getvalue())
        assert parsed == data

    def test_json_empty_list(self) -> None:
        result = DisplayResult(data=[])
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.JSON, file=buf)
        parsed = json.loads(buf.getvalue())
        assert parsed == []


# --- CSV formatter ---


class TestCsvFormatter:
    def test_csv_list(self) -> None:
        data = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        result = DisplayResult(data=data)
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.CSV, file=buf)
        buf.seek(0)
        reader = csv.DictReader(buf)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[1]["name"] == "B"

    def test_csv_with_columns(self) -> None:
        data = [{"id": "1", "name": "A", "extra": "x"}]
        columns = [ColumnDef(name="id", key="id"), ColumnDef(name="name", key="name")]
        result = DisplayResult(data=data, columns=columns)
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.CSV, file=buf)
        buf.seek(0)
        reader = csv.DictReader(buf)
        rows = list(reader)
        assert "extra" not in rows[0]
        assert rows[0]["id"] == "1"

    def test_csv_empty(self) -> None:
        result = DisplayResult(data=[])
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.CSV, file=buf)
        assert buf.getvalue() == ""

    def test_csv_detail(self) -> None:
        data = {"id": "1", "name": "Sample"}
        result = DisplayResult(data=data, is_detail=True)
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.CSV, file=buf)
        buf.seek(0)
        reader = csv.DictReader(buf)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["id"] == "1"


# --- Table formatter ---


class TestTableFormatter:
    def test_table_list(self) -> None:
        data = [{"id": "1", "name": "Sample A"}]
        result = DisplayResult(data=data, title="Test")
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.TABLE, no_color=True, file=buf)
        output = buf.getvalue()
        assert "Sample A" in output
        assert "id" in output

    def test_table_detail(self) -> None:
        data = {"id": "1", "name": "Sample A"}
        result = DisplayResult(data=data, is_detail=True, title="Detail")
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.TABLE, no_color=True, file=buf)
        output = buf.getvalue()
        assert "Sample A" in output

    def test_table_empty(self) -> None:
        result = DisplayResult(data=[])
        buf = io.StringIO()
        format_output(result, fmt=OutputFormat.TABLE, no_color=True, file=buf)
        output = buf.getvalue()
        assert "No results" in output


# --- auto_columns ---


class TestAutoColumns:
    def test_auto_columns_basic(self) -> None:
        data = [{"id": "1", "name": "A", "status": "active"}]
        cols = auto_columns(data)
        keys = [c.key for c in cols]
        assert "id" in keys
        assert "name" in keys

    def test_auto_columns_empty(self) -> None:
        assert auto_columns([]) == []

    def test_auto_columns_priority_order(self) -> None:
        data = [{"zz_field": "x", "id": "1", "name": "A"}]
        cols = auto_columns(data)
        keys = [c.key for c in cols]
        # id and name should come before zz_field
        assert keys.index("id") < keys.index("zz_field")
        assert keys.index("name") < keys.index("zz_field")
