"""Integration tests for the webhook API endpoint."""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from cappella.api.app import create_app
from cappella.config import (
    ActionConfig,
    CappellaConfig,
    TriggerConfig,
)


def _make_signature(secret: str, payload: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _config_with_webhook() -> CappellaConfig:
    return CappellaConfig(
        triggers=[
            TriggerConfig(
                name="lims-webhook",
                type="webhook",
                action=ActionConfig(type="ingest", adapter="lims"),
                webhook={
                    "path": "/webhooks/lims-ingest",
                    "secret": "api-secret-123",
                },
            ),
            TriggerConfig(
                name="nightly-ingest",
                type="schedule",
                schedule="0 2 * * *",
                action=ActionConfig(type="ingest", adapter="csv"),
            ),
        ]
    )


class TestWebhookEndpoint:
    def test_webhook_valid_request(self):
        cfg = _config_with_webhook()
        app = create_app(config=cfg)
        client = TestClient(app)

        payload = json.dumps({"sample_id": "S-001", "event": "created"}).encode()
        sig = _make_signature("api-secret-123", payload)

        resp = client.post(
            "/webhooks/lims-ingest",
            content=payload,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["trigger"] == "lims-webhook"

    def test_webhook_invalid_signature(self):
        cfg = _config_with_webhook()
        app = create_app(config=cfg)
        client = TestClient(app)

        payload = b'{"sample_id": "S-001"}'
        resp = client.post(
            "/webhooks/lims-ingest",
            content=payload,
            headers={
                "X-Hub-Signature-256": "sha256=invalid",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
        assert "invalid signature" in resp.json()["message"].lower()

    def test_webhook_unknown_path(self):
        cfg = _config_with_webhook()
        app = create_app(config=cfg)
        client = TestClient(app)

        resp = client.post(
            "/webhooks/unknown-path",
            content=b"{}",
            headers={"X-Hub-Signature-256": "sha256=x"},
        )
        assert resp.status_code == 404
        assert "no trigger registered" in resp.json()["message"].lower()

    def test_webhook_no_signature_header(self):
        cfg = _config_with_webhook()
        app = create_app(config=cfg)
        client = TestClient(app)

        resp = client.post(
            "/webhooks/lims-ingest",
            content=b'{"test": true}',
        )
        # Empty signature should fail verification
        assert resp.status_code == 401

    def test_triggers_list_includes_webhook(self):
        cfg = _config_with_webhook()
        app = create_app(config=cfg)
        client = TestClient(app)

        resp = client.get("/triggers")
        assert resp.status_code == 200
        triggers = resp.json()["triggers"]
        names = [t["name"] for t in triggers]
        assert "lims-webhook" in names
        types = {t["name"]: t["type"] for t in triggers}
        assert types["lims-webhook"] == "webhook"


class TestExistingRoutesUnchanged:
    """Verify that adding webhook support doesn't break existing routes."""

    def test_status_still_works(self):
        cfg = _config_with_webhook()
        client = TestClient(create_app(config=cfg))
        resp = client.get("/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_resolve_still_works(self):
        cfg = _config_with_webhook()
        client = TestClient(create_app(config=cfg))
        resp = client.post("/resolve", json={"entity_type": "sample"})
        assert resp.status_code == 202

    def test_trigger_run_still_works(self):
        cfg = _config_with_webhook()
        client = TestClient(create_app(config=cfg))
        resp = client.post("/triggers/nightly-ingest/run")
        assert resp.status_code == 202
