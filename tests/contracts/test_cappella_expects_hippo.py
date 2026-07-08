"""Contract tests: Cappella's behavioral expectations of MosaicClient.

These tests assert the exact behaviors Cappella depends on from MosaicClient.
They are written from Cappella's perspective — the consumer — and run against
MosaicClient directly (no Cappella code involved).

A failure here means MosaicClient changed a behavioral contract that Cappella
relies on. Treat it like a breaking API change:
  1. If the change was unintentional: fix MosaicClient.
  2. If the change was intentional: update this spec + bump Cappella's version
     to signal it may need adapter changes.

DO NOT add Hippo-internal tests here. This file only asserts what Cappella needs.

See TESTING.md for the full failure protocol.

Cappella depends on MosaicClient for:
  - Entity create/update via the ingest pipeline (IngestPipeline → put/create/update)
  - Schema-driven field validation for harmonized collections
  - schema_references() for EntityTraversal's relationship discovery
  - Provenance trail expectations (created_at, updated_at, version on entities)
  - Error handling contracts (EntityNotFoundError, ValidationFailure)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).parent.parent.parent
for _pkg in ("hippo/src", "cappella/src"):
    _p = str(_root / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from mosaic.core.client import MosaicClient
from mosaic.core.exceptions import EntityNotFoundError, ValidationFailure
from mosaic.core.storage.adapters.sqlite_adapter import SQLiteAdapter

from tests.conftest import build_test_schema_registry


@pytest.fixture()
def client(tmp_path: Path) -> MosaicClient:
    registry = build_test_schema_registry()
    storage = SQLiteAdapter(str(tmp_path / "hippo.db"), schema_registry=registry)
    return MosaicClient(storage=storage, registry=registry)


# ---------------------------------------------------------------------------
# CONTRACT: create() return shape for ingest pipeline
#
# Cappella's IngestPipeline calls hippo_client.create() for each
# transformed record. It reads the returned id and created_at to
# build audit trail entries (audit.log_run_completed).
# ---------------------------------------------------------------------------

class TestCreateForIngestContract:
    """Cappella depends on create() returning id, entity_type, data, version, created_at."""

    def test_create_returns_dict_with_id(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert isinstance(result, dict), "create() must return a dict"
        assert "id" in result, "create() must return 'id' — Cappella uses it for audit trail"
        assert isinstance(result["id"], str)

    def test_create_result_has_entity_type(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result.get("entity_type") == "Sample"

    def test_create_result_has_data_with_user_fields(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert "data" in result
        assert result["data"]["name"] == "S001"
        assert result["data"]["tissue"] == "DLPFC"

    def test_create_result_has_version(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result.get("version") == 1, "New entity must have version=1"

    def test_create_result_has_created_at(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert "created_at" in result, (
            "create() must return created_at — Cappella logs this in audit trail"
        )

    def test_create_empty_data_raises_validation_failure(self, client):
        """Cappella must be able to distinguish validation errors from other errors."""
        with pytest.raises((ValidationFailure, Exception)):
            client.create("Sample", {})


# ---------------------------------------------------------------------------
# CONTRACT: update() return shape for ingest pipeline
#
# Cappella's IngestPipeline calls update() when re-ingesting records
# from an external source that already exist in Hippo. It expects the
# returned dict to include id, version (incremented), and updated_at.
# ---------------------------------------------------------------------------

class TestUpdateForIngestContract:
    """Cappella depends on update() returning incremented version and updated_at."""

    def test_update_returns_dict_with_id(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        updated = client.update("Sample", created["id"], {"name": "S001", "tissue": "HC"})
        assert isinstance(updated, dict)
        assert updated["id"] == created["id"]

    def test_update_increments_version(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        updated = client.update("Sample", created["id"], {"name": "S001", "tissue": "HC"})
        assert updated["version"] > created["version"], (
            "update() must increment version — Cappella uses version for conflict detection"
        )

    def test_update_returns_updated_at(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        updated = client.update("Sample", created["id"], {"name": "S001", "tissue": "HC"})
        assert "updated_at" in updated, (
            "update() must return updated_at — Cappella logs this in audit trail"
        )

    def test_update_data_reflects_new_fields(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        updated = client.update("Sample", created["id"], {"name": "S001", "tissue": "HC"})
        assert updated["data"]["tissue"] == "HC", (
            "update() must reflect new field values in returned data"
        )

    def test_update_nonexistent_entity_raises_entity_not_found(self, client):
        """Cappella must get EntityNotFoundError, not a silent upsert."""
        with pytest.raises(EntityNotFoundError):
            client.update("Sample", "00000000-0000-0000-0000-000000000000", {"name": "X"})


# ---------------------------------------------------------------------------
# CONTRACT: query() return shape for EntityTraversal
#
# Cappella's EntityTraversal calls query(entity_type, criteria) to
# discover entities matching filter criteria during collection resolution.
# It iterates the result to build the datasets list.
# ---------------------------------------------------------------------------

class TestQueryForTraversalContract:
    """Cappella depends on query() returning iterable results with id and data."""

    def test_query_returns_object_with_items(self, client):
        result = client.query("Sample")
        assert hasattr(result, "items"), (
            "query() must return an object with .items — Cappella iterates this"
        )

    def test_query_items_is_iterable(self, client):
        result = client.query("Sample")
        items = list(result.items)
        assert isinstance(items, list)

    def test_query_each_item_has_id_and_data(self, client):
        client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        result = client.query("Sample")
        item = result.items[0]
        assert "id" in item, "Each item must have 'id' — Cappella reads entity_id from this"
        assert "data" in item, "Each item must have 'data' — Cappella reads fields from this"

    def test_query_with_filter_returns_matching(self, client):
        client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        client.create("Sample", {"name": "S002", "tissue": "HC"})
        result = client.query("Sample")
        assert len(result.items) == 2

    def test_query_empty_entity_type_returns_empty(self, client):
        result = client.query("NonexistentType")
        assert list(result.items) == [], (
            "query() on unknown type must return empty items, not raise — "
            "Cappella treats this as 'no datasets found'"
        )

    def test_query_limit_respected(self, client):
        for i in range(5):
            client.create("Sample", {"name": f"S{i:03d}", "tissue": "HC"})
        result = client.query("Sample", limit=2)
        assert len(result.items) <= 2, (
            "query(limit=N) must return at most N items — Cappella uses this for batched traversal"
        )


# ---------------------------------------------------------------------------
# CONTRACT: schema_references() for EntityTraversal
#
# Cappella's EntityTraversal calls schema_references(entity_type) to
# discover which child entity types to follow when traversing the
# entity graph. It expects a list (possibly empty) — never an exception.
# ---------------------------------------------------------------------------

class TestSchemaReferencesContract:
    """Cappella depends on schema_references() returning a list (not raising)."""

    def test_schema_references_returns_list(self, client):
        result = client.schema_references("Sample")
        assert isinstance(result, list), (
            "schema_references() must return a list — Cappella iterates it for traversal"
        )

    def test_schema_references_unknown_type_returns_empty_list(self, client):
        result = client.schema_references("UnknownEntityType")
        assert result == [], (
            "schema_references() on unknown type must return [] — "
            "Cappella treats this as 'no child types to traverse'"
        )


# ---------------------------------------------------------------------------
# CONTRACT: provenance trail on entities
#
# Cappella's audit module (audit.log_run_completed) and the collection
# resolver's provenance dict both depend on entities carrying temporal
# metadata. The IngestPipeline reads created_at from create() results
# and updated_at from update() results.
# ---------------------------------------------------------------------------

class TestProvenanceContract:
    """Cappella depends on temporal metadata being present on entity results."""

    def test_created_entity_has_created_at_and_updated_at(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert "created_at" in result, "Entity must have created_at for Cappella audit trail"
        assert "updated_at" in result, "Entity must have updated_at for Cappella audit trail"

    def test_get_entity_has_created_at_and_updated_at(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        fetched = client.get("Sample", created["id"])
        assert "created_at" in fetched, "get() must return created_at"
        assert "updated_at" in fetched, "get() must return updated_at"

    def test_version_monotonically_increases(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        v1 = created["version"]
        updated = client.update("Sample", created["id"], {"name": "S001", "tissue": "HC"})
        v2 = updated["version"]
        updated2 = client.update("Sample", created["id"], {"name": "S001", "tissue": "CB"})
        v3 = updated2["version"]
        assert v1 < v2 < v3, (
            "version must monotonically increase — Cappella uses this for conflict detection"
        )


# ---------------------------------------------------------------------------
# CONTRACT: error handling
#
# Cappella's IngestPipeline and EntityTraversal must be able to catch
# specific exception types to distinguish "not found" from "validation
# failure" from generic errors. These exception types must remain stable.
# ---------------------------------------------------------------------------

class TestErrorHandlingContract:
    """Cappella depends on specific exception types from MosaicClient."""

    def test_get_missing_entity_raises_entity_not_found_error(self, client):
        with pytest.raises(EntityNotFoundError):
            client.get("Sample", "00000000-0000-0000-0000-000000000000")

    def test_get_wrong_entity_type_raises_entity_not_found_error(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        with pytest.raises(EntityNotFoundError):
            client.get("WrongType", created["id"])

    def test_create_empty_data_raises_validation_failure(self, client):
        with pytest.raises(ValidationFailure):
            client.create("Sample", {})

    def test_update_deleted_entity_raises_entity_not_found(self, client):
        """After delete(), update must raise — not silently upsert."""
        created = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        client.delete("Sample", created["id"])
        with pytest.raises(EntityNotFoundError):
            client.update("Sample", created["id"], {"name": "S002", "tissue": "HC"})

    def test_entity_not_found_error_has_entity_type_and_id(self, client):
        """Cappella reads entity_type and entity_id from the exception for error reporting."""
        try:
            client.get("Sample", "00000000-0000-0000-0000-000000000000")
            pytest.fail("Expected EntityNotFoundError")
        except EntityNotFoundError as e:
            assert e.entity_type == "Sample"
            assert e.entity_id == "00000000-0000-0000-0000-000000000000"

    def test_validation_failure_has_entity_type(self, client):
        """Cappella reads entity_type from ValidationFailure for error reporting."""
        try:
            client.create("Sample", {})
            pytest.fail("Expected ValidationFailure")
        except ValidationFailure as e:
            assert e.entity_type == "Sample"
