"""Unit tests for CLI argument parsing and command registration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from aperture.cli.main import app
from aperture.models.display import OutputFormat

runner = CliRunner()


class TestCLIBasics:
    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "BASS CLI" in result.output

    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "bass 0.1.0" in result.output

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        assert result.exit_code in (0, 2)
        assert "BASS CLI" in result.output or "Usage" in result.output


class TestSchemaCommands:
    def test_schema_list_help(self) -> None:
        result = runner.invoke(app, ["schema", "list", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output

    def test_schema_show_help(self) -> None:
        result = runner.invoke(app, ["schema", "show", "--help"])
        assert result.exit_code == 0
        assert "entity_type" in result.output.lower() or "ENTITY_TYPE" in result.output


class TestConfigCommands:
    def test_config_show_help(self) -> None:
        result = runner.invoke(app, ["config", "show", "--help"])
        assert result.exit_code == 0

    def test_config_get_help(self) -> None:
        result = runner.invoke(app, ["config", "get", "--help"])
        assert result.exit_code == 0
        assert "key" in result.output.lower() or "KEY" in result.output

    def test_config_set_help(self) -> None:
        result = runner.invoke(app, ["config", "set", "--help"])
        assert result.exit_code == 0


class TestEntityCommands:
    def test_list_help(self) -> None:
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "--filter" in result.output or "-F" in result.output
        assert "--limit" in result.output

    def test_get_help(self) -> None:
        result = runner.invoke(app, ["get", "--help"])
        assert result.exit_code == 0
        assert "entity_type" in result.output.lower() or "ENTITY_TYPE" in result.output

    def test_create_help(self) -> None:
        result = runner.invoke(app, ["create", "--help"])
        assert result.exit_code == 0
        assert "--data" in result.output
        assert "--file" in result.output
        assert "--dry-run" in result.output

    def test_update_help(self) -> None:
        result = runner.invoke(app, ["update", "--help"])
        assert result.exit_code == 0
        assert "--data" in result.output

    def test_set_availability_help(self) -> None:
        result = runner.invoke(app, ["set-availability", "--help"])
        assert result.exit_code == 0


class TestSearchCommand:
    def test_search_help(self) -> None:
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--field" in result.output
        assert "--limit" in result.output


class TestHistoryCommand:
    def test_history_help(self) -> None:
        result = runner.invoke(app, ["history", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output


class TestIngestCommand:
    def test_ingest_help(self) -> None:
        result = runner.invoke(app, ["ingest", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--on-conflict" in result.output


class TestStatusCommand:
    def test_status_help(self) -> None:
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output


class TestOutputFormat:
    def test_format_enum_values(self) -> None:
        assert OutputFormat.TABLE == "table"
        assert OutputFormat.JSON == "json"
        assert OutputFormat.CSV == "csv"

    def test_format_from_string(self) -> None:
        assert OutputFormat("table") == OutputFormat.TABLE
        assert OutputFormat("json") == OutputFormat.JSON
        assert OutputFormat("csv") == OutputFormat.CSV
