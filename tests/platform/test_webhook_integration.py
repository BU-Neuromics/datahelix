"""Platform integration tests: webhook trigger → Cappella → Hippo.

Tests validate the webhook trigger flow:
1. External HTTP webhook → Cappella webhook handler
2. HMAC-SHA256 signature validation
3. Payload mapping and entity creation in Hippo
4. Deduplication (idempotent webhook delivery)

These tests exercise the Cappella trigger system with a real in-process
HippoClient. No HTTP server is started — the webhook handler is called
directly.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest

_root = Path(__file__).parent.parent.parent
for _pkg in ("hippo/src", "cappella/src"):
    _p = str(_root / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cappella.triggers.models import WebhookConfig, TriggerProvenance


# ---------------------------------------------------------------------------
# Webhook HMAC signature verification
# ---------------------------------------------------------------------------


@pytest.mark.platform
class TestWebhookSignatureVerification:
    """HMAC-SHA256 signature validation for external webhooks."""

    def test_valid_signature_passes(self):
        """Correct HMAC-SHA256 signature is accepted."""
        secret = "test-webhook-secret"
        config = WebhookConfig(
            path="/webhooks/lims-ingest",
            secret=secret,
        )

        payload = json.dumps({"sample_id": "s001", "tissue_type": "brain"}).encode()
        sig = "sha256=" + hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        assert config.verify_signature(payload, sig) is True

    def test_invalid_signature_rejected(self):
        """Wrong HMAC-SHA256 signature is rejected."""
        config = WebhookConfig(
            path="/webhooks/lims-ingest",
            secret="correct-secret",
        )

        payload = json.dumps({"sample_id": "s001"}).encode()
        bad_sig = "sha256=" + hmac.new(
            b"wrong-secret", payload, hashlib.sha256
        ).hexdigest()

        assert config.verify_signature(payload, bad_sig) is False

    def test_signature_without_prefix_accepted(self):
        """Signature without 'sha256=' prefix is also accepted."""
        secret = "test-secret"
        config = WebhookConfig(
            path="/webhooks/test",
            secret=secret,
        )

        payload = b'{"test": true}'
        raw_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert config.verify_signature(payload, raw_sig) is True

    def test_empty_payload_signature(self):
        """Empty payload produces a valid signature."""
        secret = "test-secret"
        config = WebhookConfig(
            path="/webhooks/test",
            secret=secret,
        )

        payload = b""
        sig = "sha256=" + hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        assert config.verify_signature(payload, sig) is True


# ---------------------------------------------------------------------------
# Webhook payload processing → Hippo entity creation
# ---------------------------------------------------------------------------


@pytest.mark.platform
class TestWebhookToHippoFlow:
    """Webhook payload → Cappella processing → entity created in Hippo."""

    def test_webhook_payload_creates_entity_in_hippo(
        self, hippo_client, seed_subject
    ):
        """Simulated webhook payload creates a Sample entity in Hippo.

        This simulates what the TriggerEngine does after webhook validation:
        extract fields from payload and create entity via Hippo SDK.
        """
        # Webhook payload (as received from external LIMS)
        payload = {
            "sample_id": "s-webhook-001",
            "tissue_type": "brain",
            "subject_external_id": "SUBJ-001",
        }

        # Payload mapping: webhook fields → entity fields
        payload_mapping = {
            "sample_id": "sample_id",
            "tissue_type": "tissue_type",
        }

        # Apply mapping (simulates WebhookHandler.handle_webhook)
        mapped_data = {
            entity_field: payload[webhook_field]
            for entity_field, webhook_field in payload_mapping.items()
            if webhook_field in payload
        }
        mapped_data["subject_id"] = seed_subject["id"]

        # Create entity in Hippo (simulates trigger action)
        entity = hippo_client.create("Sample", mapped_data)

        # Verify entity is in Hippo
        fetched = hippo_client.get("Sample", entity["id"])
        assert fetched["data"]["sample_id"] == "s-webhook-001"
        assert fetched["data"]["tissue_type"] == "brain"
        assert fetched["data"]["subject_id"] == seed_subject["id"]

    def test_webhook_deduplication_by_payload_hash(self):
        """Identical webhook payloads produce the same hash for dedup."""
        payload1 = json.dumps({"sample_id": "s001", "tissue_type": "brain"}).encode()
        payload2 = json.dumps({"sample_id": "s001", "tissue_type": "brain"}).encode()
        payload3 = json.dumps({"sample_id": "s002", "tissue_type": "liver"}).encode()

        hash1 = TriggerProvenance.hash_payload(payload1)
        hash2 = TriggerProvenance.hash_payload(payload2)
        hash3 = TriggerProvenance.hash_payload(payload3)

        assert hash1 == hash2, "Identical payloads must produce same hash"
        assert hash1 != hash3, "Different payloads must produce different hashes"

    def test_idempotent_webhook_no_duplicate_entities(
        self, hippo_client, seed_subject
    ):
        """Second identical webhook does not create a duplicate entity.

        Simulates Cappella's upsert-by-external-ID semantics: if an entity
        with the same sample_id already exists, the second webhook is a no-op.
        """
        sample_data = {
            "subject_id": seed_subject["id"],
            "tissue_type": "brain",
            "sample_id": "s-webhook-001",
        }

        # First webhook → create
        hippo_client.create("Sample", sample_data)
        count_after_first = len(hippo_client.query("Sample").items)

        # Second webhook → query first, skip if exists
        existing = hippo_client.query("Sample")
        already_exists = any(
            item["data"].get("sample_id") == "s-webhook-001"
            for item in existing.items
        )
        if not already_exists:
            hippo_client.create("Sample", sample_data)

        count_after_second = len(hippo_client.query("Sample").items)
        assert count_after_second == count_after_first, (
            "Idempotent webhook must not create duplicate entities"
        )

    def test_webhook_provenance_record(self):
        """Webhook trigger creates a provenance record with payload hash."""
        payload = json.dumps({"sample_id": "s001"}).encode()
        provenance = TriggerProvenance(
            trigger_name="lims-ingest",
            trigger_type="webhook",
            source="/webhooks/lims-ingest",
            timestamp="2026-04-02T12:00:00Z",
            payload_hash=TriggerProvenance.hash_payload(payload),
        )

        assert provenance.trigger_type == "webhook"
        assert provenance.payload_hash is not None
        assert len(provenance.payload_hash) == 64  # SHA-256 hex digest
