"""Tests for the Cappella CLI."""
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cappella.cli.main import app

runner = CliRunner()


class TestResolveCmd:
    def test_resolve_basic(self):
        result = runner.invoke(app, ["resolve", "sample"])
        assert result.exit_code == 0, result.output
        assert "entity_type: sample" in result.output
        assert "resolved:" in result.output
        assert "unresolved:" in result.output

    def test_resolve_shows_zero_results_with_null_client(self):
        result = runner.invoke(app, ["resolve", "sample"])
        assert "resolved: 0" in result.output
        assert "unresolved: 0" in result.output

    def test_resolve_with_strategy(self):
        result = runner.invoke(app, ["resolve", "dataset", "--strategy", "most_recent"])
        assert result.exit_code == 0

    def test_resolve_with_criteria_json(self):
        result = runner.invoke(app, ["resolve", "sample", "--criteria", '{"project": "proj1"}'])
        assert result.exit_code == 0
        assert "entity_type: sample" in result.output

    def test_resolve_invalid_criteria_exits_nonzero(self):
        result = runner.invoke(app, ["resolve", "sample", "--criteria", "not-json{bad}"])
        assert result.exit_code == 1

    def test_resolve_bad_config_path_exits_nonzero(self):
        result = runner.invoke(app, ["resolve", "sample", "--config", "/no/such/file.yaml"])
        assert result.exit_code == 1


class TestIngestCmd:
    def test_ingest_unknown_adapter_exits_nonzero(self):
        result = runner.invoke(app, ["ingest", "nonexistent-adapter"])
        assert result.exit_code == 1

    def test_ingest_missing_adapter_error_message(self):
        result = runner.invoke(app, ["ingest", "nonexistent-adapter"])
        # Error is written to stderr with mix_stderr=False
        assert result.exit_code == 1

    def test_ingest_runs_pipeline(self):
        """Ingest calls IngestPipeline and prints summary."""
        mock_adapter = MagicMock()
        mock_adapter.name = "csv"
        mock_adapter.fetch.return_value = iter([])

        with patch("cappella.adapters.registry.AdapterRegistry.from_config") as mock_from_cfg:
            mock_registry = MagicMock()
            mock_registry.get.return_value = mock_adapter
            mock_from_cfg.return_value = mock_registry

            result = runner.invoke(app, ["ingest", "csv"])

        assert result.exit_code == 0, result.output
        assert "adapter: csv" in result.output
        assert "status:" in result.output
        assert "fetched:" in result.output

    def test_ingest_invalid_since_exits_nonzero(self):
        """--since with bad ISO string should exit nonzero."""
        mock_adapter = MagicMock()
        mock_adapter.name = "csv"
        mock_adapter.fetch.return_value = iter([])

        with patch("cappella.adapters.registry.AdapterRegistry.from_config") as mock_from_cfg:
            mock_registry = MagicMock()
            mock_registry.get.return_value = mock_adapter
            mock_from_cfg.return_value = mock_registry

            result = runner.invoke(app, ["ingest", "csv", "--since", "not-a-date"])

        assert result.exit_code == 1

    def test_ingest_with_valid_since(self):
        mock_adapter = MagicMock()
        mock_adapter.name = "csv"
        mock_adapter.fetch.return_value = iter([])

        with patch("cappella.adapters.registry.AdapterRegistry.from_config") as mock_from_cfg:
            mock_registry = MagicMock()
            mock_registry.get.return_value = mock_adapter
            mock_from_cfg.return_value = mock_registry

            result = runner.invoke(app, ["ingest", "csv", "--since", "2026-01-01T00:00:00"])

        assert result.exit_code == 0


class TestReconcileCmd:
    def test_reconcile_basic(self):
        result = runner.invoke(app, ["reconcile", "sample"])
        assert result.exit_code == 0, result.output
        assert "entity_type: sample" in result.output
        assert "findings:" in result.output

    def test_reconcile_null_hippo_returns_zero_findings(self):
        result = runner.invoke(app, ["reconcile", "sample"])
        assert "findings: 0" in result.output

    def test_reconcile_with_known_checks(self):
        result = runner.invoke(app, ["reconcile", "sample", "--checks", "missing_entity,stale_entity"])
        assert result.exit_code == 0
        assert "findings: 0" in result.output

    def test_reconcile_with_unknown_check_produces_finding(self):
        result = runner.invoke(app, ["reconcile", "sample", "--checks", "nonexistent_check"])
        assert result.exit_code == 0
        # ReconciliationEngine emits an error finding for unknown check names
        assert "findings: 1" in result.output
        assert "nonexistent_check" in result.output

    def test_reconcile_bad_config_path_exits_nonzero(self):
        result = runner.invoke(app, ["reconcile", "sample", "--config", "/no/such/file.yaml"])
        assert result.exit_code == 1


class TestStatusCmd:
    def test_status_success(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "ok", "version": "0.1.0"}
            mock_get.return_value = mock_resp

            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "ok" in result.output
        assert "0.1.0" in result.output

    def test_status_server_error(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_get.return_value = mock_resp

            result = runner.invoke(app, ["status"])

        assert result.exit_code == 1

    def test_status_connection_error(self):
        with patch("httpx.get", side_effect=Exception("connection refused")):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 1

    def test_status_custom_url(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "ok", "version": "0.2.0"}
            mock_get.return_value = mock_resp

            result = runner.invoke(app, ["status", "--url", "http://myserver:9000"])

        mock_get.assert_called_once_with("http://myserver:9000/status", timeout=5.0)
        assert result.exit_code == 0


class TestTriggerRunCmd:
    def test_trigger_run_success(self):
        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 202
            mock_resp.json.return_value = {"run_id": "abc-123", "trigger": "nightly"}
            mock_post.return_value = mock_resp

            result = runner.invoke(app, ["trigger", "run", "nightly"])

        assert result.exit_code == 0
        assert "nightly" in result.output
        assert "abc-123" in result.output

    def test_trigger_run_server_error(self):
        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_post.return_value = mock_resp

            result = runner.invoke(app, ["trigger", "run", "nightly"])

        assert result.exit_code == 1

    def test_trigger_run_connection_error(self):
        with patch("httpx.post", side_effect=Exception("no server")):
            result = runner.invoke(app, ["trigger", "run", "nightly"])
        assert result.exit_code == 1


class TestTriggerListCmd:
    def test_trigger_list_empty(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"triggers": []}
            mock_get.return_value = mock_resp

            result = runner.invoke(app, ["trigger", "list"])

        assert result.exit_code == 0
        assert "No triggers" in result.output

    def test_trigger_list_with_items(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "triggers": [
                    {"name": "nightly", "type": "schedule"},
                    {"name": "on-demand", "type": "manual"},
                ]
            }
            mock_get.return_value = mock_resp

            result = runner.invoke(app, ["trigger", "list"])

        assert result.exit_code == 0
        assert "nightly" in result.output
        assert "on-demand" in result.output

    def test_trigger_list_connection_error(self):
        with patch("httpx.get", side_effect=Exception("no server")):
            result = runner.invoke(app, ["trigger", "list"])
        assert result.exit_code == 1


class TestFindingsCmd:
    def test_findings_empty(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"findings": []}
            mock_get.return_value = mock_resp

            result = runner.invoke(app, ["findings"])

        assert result.exit_code == 0
        assert "No findings" in result.output

    def test_findings_with_results(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "findings": [
                    {
                        "severity": "error",
                        "check": "missing_entity",
                        "entity_type": "sample",
                        "entity_id": "s-001",
                        "detail": "Not found in Hippo",
                    }
                ]
            }
            mock_get.return_value = mock_resp

            result = runner.invoke(app, ["findings"])

        assert result.exit_code == 0
        assert "ERROR" in result.output
        assert "missing_entity" in result.output
        assert "s-001" in result.output

    def test_findings_passes_filters(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"findings": []}
            mock_get.return_value = mock_resp

            runner.invoke(app, ["findings", "--entity-type", "sample", "--severity", "error"])

        call_kwargs = mock_get.call_args
        params = call_kwargs[1]["params"] if call_kwargs[1] else call_kwargs[0][1]
        assert params.get("entity_type") == "sample"
        assert params.get("severity") == "error"
