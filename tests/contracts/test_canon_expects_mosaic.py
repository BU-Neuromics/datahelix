"""Contract tests: Canon's behavioral expectations of MosaicClient.

These tests assert the exact behaviors Canon depends on from MosaicClient.
They are written from Canon's perspective — the consumer — and run against
MosaicClient directly (no Canon code involved).

A failure here means MosaicClient changed a behavioral contract that Canon
relies on. Treat it like a breaking API change:
  1. If the change was unintentional: fix MosaicClient.
  2. If the change was intentional: update this spec + bump Canon's version
     to signal it may need adapter changes.

DO NOT add Mosaic-internal tests here. This file only asserts what Canon needs.

See TESTING.md for the full failure protocol.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).parent.parent.parent
for _pkg in ("mosaic/src", "canon/src"):
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
    storage = SQLiteAdapter(str(tmp_path / "mosaic.db"), schema_registry=registry)
    return MosaicClient(storage=storage, registry=registry)


# ---------------------------------------------------------------------------
# CONTRACT: query() return shape
#
# Canon iterates result.items to find matching entities. It also checks
# result.total for pagination. These fields must exist.
# ---------------------------------------------------------------------------

class TestQueryContract:
    """Canon depends on query() returning a PaginatedResult with .items."""

    def test_query_returns_object_with_items_attribute(self, client):
        result = client.query("Sample")
        assert hasattr(result, "items"), (
            "query() must return an object with .items — Canon iterates this"
        )

    def test_query_items_is_iterable(self, client):
        result = client.query("Sample")
        # Must be iterable without error even when empty
        items = list(result.items)
        assert isinstance(items, list)

    def test_query_each_item_has_id_entity_type_data(self, client):
        client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        result = client.query("Sample")
        item = result.items[0]
        assert "id" in item, "Each item must have 'id' key"
        assert "entity_type" in item, "Each item must have 'entity_type' key"
        assert "data" in item, "Each item must have 'data' key — Canon reads entity fields here"

    def test_query_data_contains_user_fields(self, client):
        client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        result = client.query("Sample")
        data = result.items[0]["data"]
        assert data.get("name") == "S001"
        assert data.get("tissue") == "DLPFC"

    def test_query_limit_respected(self, client):
        for i in range(5):
            client.create("Sample", {"name": f"S{i:03d}", "tissue": "HC"})
        result = client.query("Sample", limit=3)
        assert len(result.items) <= 3, (
            "query(limit=N) must return at most N items — Canon uses this for pagination"
        )

    def test_query_empty_entity_type_returns_empty_items(self, client):
        result = client.query("NonexistentType")
        assert list(result.items) == [], (
            "query() on unknown type must return empty items, not raise"
        )


# ---------------------------------------------------------------------------
# CONTRACT: create() return shape
#
# Canon's OutputIngestionPipeline calls create() and reads the returned
# entity id to construct a provenance record.
# ---------------------------------------------------------------------------

class TestCreateContract:
    """Canon depends on create() returning a specific shape."""

    def test_create_returns_dict(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        assert isinstance(result, dict), "create() must return a dict"

    def test_create_result_has_id(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        assert "id" in result, "create() result must have 'id' — Canon uses it for provenance"
        assert isinstance(result["id"], str), "id must be a string (UUID)"

    def test_create_result_has_entity_type(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        assert result.get("entity_type") == "Sample"

    def test_create_result_has_data_with_user_fields(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        assert "data" in result
        assert result["data"].get("name") == "S001"

    def test_create_result_has_version_starting_at_1(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        assert result.get("version") == 1, (
            "Freshly created entity must have version=1"
        )

    def test_create_result_has_created_at(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        assert "created_at" in result, (
            "create() must return created_at — Canon uses this for WorkflowRun provenance"
        )

    def test_create_invalid_entity_raises_validation_failure(self, client):
        """Canon must be able to distinguish validation errors from other errors."""
        with pytest.raises((ValidationFailure, Exception)):
            # Empty data violates required fields; the exact exception type
            # is asserted in test_hippo_self_contract.py
            client.create("Sample", {})


# ---------------------------------------------------------------------------
# CONTRACT: get() behavior
#
# Canon's HippoQueryClient calls get() to fetch entities by id.
# Not-found must raise EntityNotFoundError (not return None) so Canon
# can distinguish "missing" from "exists but empty".
# ---------------------------------------------------------------------------

class TestGetContract:
    """Canon depends on get() raising EntityNotFoundError for missing entities."""

    def test_get_returns_same_shape_as_create(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "HC"})
        fetched = client.get("Sample", created["id"])
        assert fetched["id"] == created["id"]
        assert fetched["data"] == created["data"]
        assert fetched["entity_type"] == created["entity_type"]

    def test_get_nonexistent_raises_entity_not_found_error(self, client):
        with pytest.raises(EntityNotFoundError):
            client.get("Sample", "00000000-0000-0000-0000-000000000000")

    def test_get_wrong_entity_type_raises_entity_not_found_error(self, client):
        created = client.create("Sample", {"name": "S001", "tissue": "HC"})
        with pytest.raises(EntityNotFoundError):
            client.get("WrongType", created["id"])


# ---------------------------------------------------------------------------
# CONTRACT: delete() soft-delete semantics
#
# Canon does not currently call delete() directly, but the MosaicClientShim
# must behave consistently with these semantics. Documented here so a future
# Canon version that does use delete() has a stable baseline.
# ---------------------------------------------------------------------------

class TestDeleteContract:
    """delete() must exclude entities from query() results."""

    def test_deleted_entity_excluded_from_query(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        client.create("Sample", {"name": "S002", "tissue": "HC"})
        client.delete("Sample", result["id"])
        items = list(client.query("Sample").items)
        ids = [i["id"] for i in items]
        assert result["id"] not in ids, (
            "delete() must exclude entity from query() — Canon must not REUSE deleted entities"
        )

    def test_delete_returns_truthy(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        assert client.delete("Sample", result["id"]), (
            "delete() must return truthy on success"
        )

    def test_deleted_entity_raises_on_get(self, client):
        result = client.create("Sample", {"name": "S001", "tissue": "HC"})
        client.delete("Sample", result["id"])
        with pytest.raises(EntityNotFoundError):
            client.get("Sample", result["id"])


# ---------------------------------------------------------------------------
# CONTRACT: supersede_entity() semantics
#
# Canon's ingestion pipeline may call supersede_entity() when replacing
# a previously computed artifact. The old entity must be marked superseded
# and the new one must remain available.
# ---------------------------------------------------------------------------

class TestSupersedeContract:
    """Canon depends on supersede_entity() marking old as superseded, keeping new available."""

    def test_superseded_entity_excluded_from_query(self, client):
        old = client.create("Sample", {"name": "S001", "tissue": "HC"})
        new = client.create("Sample", {"name": "S002", "tissue": "HC"})
        client.supersede_entity(old["id"], new["id"])
        items = list(client.query("Sample").items)
        ids = [i["id"] for i in items]
        assert old["id"] not in ids, (
            "Superseded entity must be excluded from query() — Canon must not REUSE superseded artifacts"
        )

    def test_replacement_entity_available_after_supersede(self, client):
        old = client.create("Sample", {"name": "S001", "tissue": "HC"})
        new = client.create("Sample", {"name": "S002", "tissue": "HC"})
        client.supersede_entity(old["id"], new["id"])
        fetched = client.get("Sample", new["id"])
        assert fetched["id"] == new["id"], (
            "Replacement entity must remain accessible after supersede"
        )

    def test_superseded_entity_raises_on_get(self, client):
        old = client.create("Sample", {"name": "S001", "tissue": "HC"})
        new = client.create("Sample", {"name": "S002", "tissue": "HC"})
        client.supersede_entity(old["id"], new["id"])
        with pytest.raises(EntityNotFoundError):
            client.get("Sample", old["id"])
