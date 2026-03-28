"""Tests for the Cappella FastAPI application."""
import pytest
from fastapi.testclient import TestClient

from cappella.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


class TestStatusRoute:
    def test_status_ok(self, client):
        resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestResolveRoutes:
    def test_start_resolve_returns_202(self, client):
        resp = client.post("/resolve", json={"entity_type": "sample"})
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        assert data["status"] == "queued"

    def test_get_resolve_status(self, client):
        resp = client.post("/resolve", json={"entity_type": "sample"})
        run_id = resp.json()["run_id"]

        resp2 = client.get(f"/resolve/{run_id}")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["run_id"] == run_id
        assert data["job_type"] == "resolve"

    def test_get_resolve_status_not_found(self, client):
        resp = client.get("/resolve/nonexistent-run-id")
        assert resp.status_code == 404

    def test_multiple_resolve_jobs_are_independent(self, client):
        r1 = client.post("/resolve", json={})
        r2 = client.post("/resolve", json={})
        id1 = r1.json()["run_id"]
        id2 = r2.json()["run_id"]
        assert id1 != id2
        assert client.get(f"/resolve/{id1}").status_code == 200
        assert client.get(f"/resolve/{id2}").status_code == 200


class TestIngestRoutes:
    def test_start_ingest_returns_202(self, client):
        resp = client.post("/ingest/csv", json={})
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        assert data["adapter"] == "csv"
        assert data["status"] == "queued"

    def test_get_ingest_status(self, client):
        resp = client.post("/ingest/json", json={})
        run_id = resp.json()["run_id"]

        resp2 = client.get(f"/ingest/{run_id}")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["run_id"] == run_id
        assert data["job_type"] == "ingest"

    def test_get_ingest_status_not_found(self, client):
        resp = client.get("/ingest/no-such-job")
        assert resp.status_code == 404

    def test_ingest_stores_adapter_name(self, client):
        resp = client.post("/ingest/xml", json={})
        run_id = resp.json()["run_id"]
        job = client.get(f"/ingest/{run_id}").json()
        assert job["adapter"] == "xml"


class TestTriggerRoutes:
    def test_run_trigger_returns_202(self, client):
        resp = client.post("/triggers/my-trigger/run")
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        assert data["trigger"] == "my-trigger"
        assert data["status"] == "queued"

    def test_list_triggers_empty(self, client):
        resp = client.get("/triggers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["triggers"] == []

    def test_list_triggers_with_config(self):
        from cappella.config import ActionConfig, CappellaConfig, TriggerConfig

        cfg = CappellaConfig(
            triggers=[
                TriggerConfig(
                    name="nightly-ingest",
                    type="schedule",
                    schedule="0 2 * * *",
                    action=ActionConfig(type="ingest", adapter="csv"),
                )
            ]
        )
        with TestClient(create_app(config=cfg)) as c:
            resp = c.get("/triggers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["triggers"]) == 1
        assert data["triggers"][0]["name"] == "nightly-ingest"
        assert data["triggers"][0]["type"] == "schedule"


class TestReconcileRoutes:
    def test_reconcile_returns_findings_key(self, client):
        resp = client.post("/reconcile", json={"entity_type": "sample"})
        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data
        assert isinstance(data["findings"], list)

    def test_reconcile_echoes_entity_type(self, client):
        resp = client.post("/reconcile", json={"entity_type": "dataset"})
        assert resp.json()["entity_type"] == "dataset"

    def test_get_findings_empty(self, client):
        resp = client.get("/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["findings"] == []

    def test_get_findings_with_filters(self, client):
        resp = client.get("/findings", params={"entity_type": "sample", "severity": "error"})
        assert resp.status_code == 200
        assert "findings" in resp.json()

    def test_get_findings_with_stored_finding(self):
        """Findings stored in FindingsStore are returned by GET /findings."""
        from cappella.reconciliation.engine import ReconciliationFinding

        app = create_app()
        finding = ReconciliationFinding(
            finding_id="f-001",
            check="missing_entity",
            entity_type="sample",
            entity_id="s-123",
            severity="error",
            detail="Entity not found",
            suggested_action="Create the entity",
        )
        app.state.findings_store.store(finding)

        with TestClient(app) as c:
            resp = c.get("/findings")
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        assert len(findings) == 1
        assert findings[0]["finding_id"] == "f-001"
        assert findings[0]["check"] == "missing_entity"
        assert findings[0]["severity"] == "error"

    def test_get_findings_filtered_by_entity_type(self):
        from cappella.reconciliation.engine import ReconciliationFinding

        app = create_app()
        for etype, eid in [("sample", "s-1"), ("dataset", "d-1")]:
            app.state.findings_store.store(
                ReconciliationFinding(
                    finding_id=f"f-{eid}",
                    check="missing_entity",
                    entity_type=etype,
                    entity_id=eid,
                    severity="error",
                    detail="Not found",
                    suggested_action="Fix it",
                )
            )

        with TestClient(app) as c:
            resp = c.get("/findings", params={"entity_type": "sample"})
        findings = resp.json()["findings"]
        assert len(findings) == 1
        assert findings[0]["entity_type"] == "sample"


class TestErrorHandlers:
    def test_404_for_unknown_route(self, client):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404

    def test_config_error_returns_400(self):
        from cappella.exceptions import ConfigError

        app = create_app()

        @app.get("/raise-config-error")
        async def _raise():
            raise ConfigError("bad config", {"key": "val"})

        with TestClient(app) as c:
            resp = c.get("/raise-config-error")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "ConfigError"
        assert "bad config" in data["message"]

    def test_reconciliation_error_returns_422(self):
        from cappella.exceptions import ReconciliationError

        app = create_app()

        @app.get("/raise-recon-error")
        async def _raise():
            raise ReconciliationError("recon failed")

        with TestClient(app) as c:
            resp = c.get("/raise-recon-error")
        assert resp.status_code == 422
        assert resp.json()["error"] == "ReconciliationError"
