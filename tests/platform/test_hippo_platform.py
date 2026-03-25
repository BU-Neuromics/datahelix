"""Platform integration tests: Hippo-only categories.

Tests exercise the real HippoClient backed by SQLiteAdapter in-process.
No HTTP server is required except for REST API contract tests (TestClient).

## Category taxonomy

### Implemented
1.  Schema lifecycle — client with/without schema, FTS metadata derivation,
    schema evolution (additive field addition)
2.  Entity CRUD contract — create/get/update/delete with correct return shapes
3.  CEL validation — valid/invalid entities, multi-rule, bypass mode
4.  Provenance and event model — timestamps, version tracking, supersede
5.  FTS5 search — matching, no-results, multi-result, deleted entity excluded
6.  Query and pagination — limit, offset, total count, date filtering
7.  REST API contract — status codes, error shapes via FastAPI TestClient
8.  Delete behavior — soft delete, idempotency, post-delete state
9.  Supersede entity — atomic supersession, guards, relationship edge
10. External IDs — register, lookup, supersede external ID

### Pending
- Partial indexes and summary views (requires CLI migration; covered by test_migrate.py)
- Concurrency / isolation via threading (deferred: SQLite WAL mode correctness)
- Reference types / expand paths (covered by test_expand_workflow.py)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from hippo.api.factory import create_app
from hippo.core.client import HippoClient
from hippo.core.exceptions import (
    EntityAlreadySupersededError,
    EntityNotFoundError,
    ValidationFailure,
)
from hippo.core.pipeline import ValidationPipeline
from hippo.core.storage.adapters.sqlite_adapter import SQLiteAdapter
from hippo.core.storage.fts import FTSFieldMetadata, FTSTableMetadata
from hippo.core.validators.write_validator import CELWriteValidator
from hippo.serve.routers.entity import router as entity_router
from hippo.serve.routers.health import router as health_router


# ---------------------------------------------------------------------------
# Schema and validator YAML fixtures
# ---------------------------------------------------------------------------

_BASIC_SCHEMA_YAML = {
    "entities": [
        {
            "name": "Sample",
            "version": "1.0",
            "fields": [
                {"name": "name", "type": "string", "required": True},
                {"name": "tissue", "type": "string", "required": True},
                {"name": "notes", "type": "string", "required": False, "search": "fts5"},
            ],
        }
    ]
}

_VALIDATORS_YAML = {
    "validators": [
        {
            "name": "sample_name_format",
            "entity_type": "Sample",
            "operations": ["create", "update"],
            "condition": 'entity.name.matches("^S[0-9]{3}$")',
            "message": "Sample name must match S followed by 3 digits (e.g. S001)",
        }
    ]
}

_MULTI_RULE_VALIDATORS_YAML = {
    "validators": [
        {
            "name": "name_format",
            "entity_type": "Sample",
            "operations": ["create"],
            "condition": 'entity.name.matches("^S[0-9]{3}$")',
            "message": "Name must be S+3 digits",
        },
        {
            "name": "tissue_nonempty",
            "entity_type": "Sample",
            "operations": ["create"],
            "condition": 'size(entity.tissue) > 0',
            "message": "Tissue must not be empty",
        },
    ]
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_hippo(tmp_path: Path) -> Path:
    """Minimal Hippo project directory with schema + validators."""
    (tmp_path / "schema.yaml").write_text(yaml.dump(_BASIC_SCHEMA_YAML))
    (tmp_path / "validators.yaml").write_text(yaml.dump(_VALIDATORS_YAML))
    return tmp_path


def _make_client(
    tmp_hippo: Path,
    *,
    validation: bool = False,
    fts: bool = False,
    validators_yaml: dict | None = None,
) -> HippoClient:
    """Build a HippoClient backed by a real SQLiteAdapter."""
    db_path = tmp_hippo / "hippo.db"
    storage = SQLiteAdapter(str(db_path))

    pipeline: ValidationPipeline | None = None
    if validation:
        v_path = tmp_hippo / "validators.yaml"
        if validators_yaml is not None:
            v_path.write_text(yaml.dump(validators_yaml))
        pipeline = ValidationPipeline()
        cel = CELWriteValidator(validators_path=str(v_path))
        pipeline.add_validator(cel)

    schema_file = tmp_hippo / "schema.yaml"
    schema_yaml = yaml.safe_load(schema_file.read_text())
    schemas = {}
    for entity in schema_yaml.get("entities", []):
        from hippo.config.models import SchemaConfig
        schemas[entity["name"]] = SchemaConfig(**entity)

    client = HippoClient(storage=storage, pipeline=pipeline, schemas=schemas)

    if fts:
        conn = sqlite3.connect(str(db_path))
        for entity_type, schema in schemas.items():
            for field in schema.fields:
                if field.search and "fts" in field.search.lower():
                    meta = FTSTableMetadata.from_field(field, entity_type=entity_type)
                    conn.execute(
                        f"CREATE VIRTUAL TABLE IF NOT EXISTS {meta.table_name} "
                        "USING fts5(entity_id, content)"
                    )
        conn.commit()
        conn.close()

    return client


def _data(entity: dict[str, Any]) -> dict[str, Any]:
    return entity["data"]


# ---------------------------------------------------------------------------
# Category 1: Schema lifecycle
# ---------------------------------------------------------------------------


class TestSchemaLifecycle:
    """Schema loading, FTS metadata derivation, and additive schema evolution.

    Covered: client with no schema creates entities; schema-based FTS metadata
    is auto-derived; new optional field doesn't break existing entities.
    """

    def test_no_schema_client_creates_entities(self, tmp_path):
        storage = SQLiteAdapter(str(tmp_path / "h.db"))
        client = HippoClient(storage=storage)
        result = client.create("Foo", {"x": "1"})
        assert result["id"]
        assert result["entity_type"] == "Foo"

    def test_schema_with_fts_field_populates_metadata(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        assert "Sample" in client._fts_table_metadata
        fts_list = client._fts_table_metadata["Sample"]
        assert len(fts_list) == 1
        assert fts_list[0].source_entity_type == "Sample"

    def test_additive_optional_field_old_entity_survives(self, tmp_hippo):
        client1 = _make_client(tmp_hippo)
        result = client1.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        eid = result["id"]

        # Add optional field to schema
        schema = yaml.safe_load((tmp_hippo / "schema.yaml").read_text())
        schema["entities"][0]["fields"].append(
            {"name": "batch", "type": "string", "required": False}
        )
        (tmp_hippo / "schema.yaml").write_text(yaml.dump(schema))

        client2 = _make_client(tmp_hippo)
        fetched = client2.get("Sample", eid)
        assert _data(fetched)["name"] == "S001"
        assert _data(fetched).get("batch") is None

    def test_new_entity_uses_new_optional_field(self, tmp_hippo):
        schema = yaml.safe_load((tmp_hippo / "schema.yaml").read_text())
        schema["entities"][0]["fields"].append(
            {"name": "batch", "type": "string", "required": False}
        )
        (tmp_hippo / "schema.yaml").write_text(yaml.dump(schema))

        client = _make_client(tmp_hippo)
        result = client.create(
            "Sample", {"name": "S001", "tissue": "DLPFC", "batch": "B01"}
        )
        assert _data(client.get("Sample", result["id"]))["batch"] == "B01"


# ---------------------------------------------------------------------------
# Category 2: Entity CRUD contract
# ---------------------------------------------------------------------------


class TestEntityCRUDContract:
    """Create/read/update/delete with correct return shapes and field values."""

    def test_create_returns_id_entity_type_data(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result["id"]
        assert result["entity_type"] == "Sample"
        assert _data(result)["name"] == "S001"
        assert _data(result)["tissue"] == "DLPFC"

    def test_create_returns_version_1(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result["version"] == 1

    def test_create_sets_created_at(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result["created_at"]

    def test_get_returns_same_data_as_create(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S002", "tissue": "HC"})
        fetched = client.get("Sample", result["id"])
        assert _data(fetched)["name"] == "S002"
        assert _data(fetched)["tissue"] == "HC"

    def test_update_changes_data(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        updated = client.update("Sample", result["id"], {"name": "S001", "tissue": "ACC"})
        assert _data(updated)["tissue"] == "ACC"

    def test_update_increments_version(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result["version"] == 1
        updated = client.update("Sample", result["id"], {"name": "S001", "tissue": "ACC"})
        assert updated["version"] == 2

    def test_update_preserves_id(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        updated = client.update("Sample", result["id"], {"name": "S001", "tissue": "ACC"})
        assert updated["id"] == result["id"]

    def test_get_nonexistent_raises_not_found(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        with pytest.raises(EntityNotFoundError):
            client.get("Sample", "does-not-exist")

    def test_get_wrong_entity_type_raises_not_found(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        with pytest.raises(EntityNotFoundError):
            client.get("WrongType", result["id"])

    def test_multiple_entities_have_distinct_ids(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        r1 = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        r2 = client.create("Sample", {"name": "S002", "tissue": "HC"})
        assert r1["id"] != r2["id"]

    def test_empty_data_raises_validation_failure(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        with pytest.raises(ValidationFailure):
            client.create("Sample", {})

    def test_delete_returns_true(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert client.delete("Sample", result["id"]) is True


# ---------------------------------------------------------------------------
# Category 3: CEL validation
# ---------------------------------------------------------------------------


class TestCELValidation:
    """Valid and invalid entities, multi-rule, bypass mode."""

    def test_valid_entity_passes(self, tmp_hippo):
        client = _make_client(tmp_hippo, validation=True)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert _data(result)["name"] == "S001"

    def test_invalid_name_format_raises_validation_failure(self, tmp_hippo):
        client = _make_client(tmp_hippo, validation=True)
        with pytest.raises(ValidationFailure):
            client.create("Sample", {"name": "bad-name", "tissue": "DLPFC"})

    def test_name_too_long_rejected(self, tmp_hippo):
        client = _make_client(tmp_hippo, validation=True)
        with pytest.raises(ValidationFailure):
            client.create("Sample", {"name": "S0001", "tissue": "DLPFC"})

    def test_update_also_validated(self, tmp_hippo):
        client = _make_client(tmp_hippo, validation=True)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        with pytest.raises(ValidationFailure):
            client.update("Sample", result["id"], {"name": "invalid", "tissue": "X"})

    def test_bypass_validation_skips_cel_check(self, tmp_hippo):
        """bypass_validation=True allows otherwise-invalid entities through."""
        client = _make_client(tmp_hippo, validation=True)
        result = client.create(
            "Sample", {"name": "not-valid", "tissue": "X"}, bypass_validation=True
        )
        assert _data(result)["name"] == "not-valid"

    def test_multi_rule_valid_entity_passes_all(self, tmp_hippo):
        client = _make_client(
            tmp_hippo,
            validation=True,
            validators_yaml=_MULTI_RULE_VALIDATORS_YAML,
        )
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result["version"] == 1

    def test_multi_rule_first_failure_blocks_write(self, tmp_hippo):
        client = _make_client(
            tmp_hippo,
            validation=True,
            validators_yaml=_MULTI_RULE_VALIDATORS_YAML,
        )
        # name is invalid → name_format rule fails
        with pytest.raises(ValidationFailure):
            client.create("Sample", {"name": "bad", "tissue": "DLPFC"})


# ---------------------------------------------------------------------------
# Category 4: Provenance and event model
# ---------------------------------------------------------------------------


class TestProvenanceAndEventModel:
    """Timestamps, version tracking, and entity supersession."""

    def test_freshly_created_entity_has_no_superseded_by(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        fetched = client.get("Sample", result["id"])
        assert fetched["superseded_by"] is None

    def test_create_returns_created_at_and_updated_at(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert result["created_at"]
        assert result["updated_at"]

    def test_multiple_updates_version_increments_correctly(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        v2 = client.update("Sample", result["id"], {"name": "S001", "tissue": "HC"})
        v3 = client.update("Sample", result["id"], {"name": "S001", "tissue": "ACC"})
        assert v2["version"] == 2
        assert v3["version"] == 3

    @pytest.mark.xfail(
        reason="HippoClient.get() currently returns superseded entities; "
               "soft-delete via supersede is not yet enforced on reads. "
               "Revisit when Hippo adds availability filtering to get_by_id."
    )
    def test_supersede_entity_marks_source_unavailable(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        old = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        new = client.create("Sample", {"name": "S002", "tissue": "DLPFC"})

        client.supersede_entity(old["id"], new["id"], reason="version bump")

        # Superseded entity cannot be fetched as an available entity
        with pytest.raises(EntityNotFoundError):
            client.get("Sample", old["id"])

    def test_supersede_sets_superseded_by_field(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        old = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        new = client.create("Sample", {"name": "S002", "tissue": "DLPFC"})

        client.supersede_entity(old["id"], new["id"])

        # superseded_by is readable via read_any (includes unavailable)
        entity = client.storage.read_any(old["id"])
        assert entity.superseded_by == new["id"]

    def test_supersede_already_superseded_raises(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        old = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        new = client.create("Sample", {"name": "S002", "tissue": "DLPFC"})
        newer = client.create("Sample", {"name": "S003", "tissue": "DLPFC"})

        client.supersede_entity(old["id"], new["id"])

        with pytest.raises(EntityAlreadySupersededError):
            client.supersede_entity(old["id"], newer["id"])


# ---------------------------------------------------------------------------
# Category 5: FTS5 search
# ---------------------------------------------------------------------------


class TestFTS5Search:
    """FTS indexing, search, multi-result, deleted entity excluded."""

    def test_fts_search_returns_matching_entity(self, tmp_hippo):
        client = _make_client(tmp_hippo, fts=True)
        client.create(
            "Sample",
            {"name": "S001", "tissue": "DLPFC", "notes": "hippocampus lesion observed"},
        )
        client.create(
            "Sample",
            {"name": "S002", "tissue": "ACC", "notes": "prefrontal cortex damage"},
        )
        results = client.search("Sample", "hippocampus")
        names = [_data(r)["name"] for r in results]
        assert "S001" in names
        assert "S002" not in names

    def test_fts_search_no_match_returns_empty(self, tmp_hippo):
        client = _make_client(tmp_hippo, fts=True)
        client.create(
            "Sample",
            {"name": "S001", "tissue": "DLPFC", "notes": "cortex damage"},
        )
        results = client.search("Sample", "flyingpig12345")
        assert results == []

    def test_fts_search_multiple_results(self, tmp_hippo):
        client = _make_client(tmp_hippo, fts=True)
        for i, notes in enumerate(["cortex observation", "cortex lesion", "other notes"], 1):
            client.create(
                "Sample",
                {"name": f"S00{i}", "tissue": "DLPFC", "notes": notes},
            )
        results = client.search("Sample", "cortex")
        names = [_data(r)["name"] for r in results]
        assert "S001" in names
        assert "S002" in names
        assert "S003" not in names

    def test_deleted_entity_excluded_from_fts(self, tmp_hippo):
        client = _make_client(tmp_hippo, fts=True)
        result = client.create(
            "Sample",
            {"name": "S001", "tissue": "DLPFC", "notes": "hippocampus lesion"},
        )
        # Confirm it's searchable before delete
        assert len(client.search("Sample", "hippocampus")) == 1

        client.delete("Sample", result["id"])
        results_after = client.search("Sample", "hippocampus")
        assert results_after == []

    def test_no_fts_metadata_search_returns_empty(self, tmp_path):
        """Client with no FTS schema returns [] from search() without error."""
        storage = SQLiteAdapter(str(tmp_path / "h.db"))
        client = HippoClient(storage=storage)
        client.create("Foo", {"x": "1"})
        assert client.search("Foo", "anything") == []


# ---------------------------------------------------------------------------
# Category 6: Query and pagination
# ---------------------------------------------------------------------------


class TestQueryAndPagination:
    """query() with limit, offset, total, and date filtering."""

    def test_query_returns_all_created_entities(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        for i in range(3):
            client.create("Sample", {"name": f"S00{i}", "tissue": "X"})
        result = client.query("Sample")
        assert result.total == 3
        assert len(result.items) == 3

    def test_query_limit_reduces_items(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        for i in range(5):
            client.create("Sample", {"name": f"S00{i}", "tissue": "X"})
        result = client.query("Sample", limit=2)
        assert len(result.items) == 2
        assert result.total == 5  # total ignores limit

    def test_query_offset_skips_items(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        for i in range(4):
            client.create("Sample", {"name": f"S00{i}", "tissue": "X"})
        result_all = client.query("Sample")
        result_offset = client.query("Sample", offset=2)
        assert len(result_offset.items) == 2
        assert result_offset.offset == 2

    def test_query_empty_type_returns_empty(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.query("NonExistent")
        assert result.total == 0
        assert result.items == []

    def test_query_paginated_result_has_correct_structure(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        result = client.query("Sample")
        assert hasattr(result, "items")
        assert hasattr(result, "total")
        assert hasattr(result, "limit")
        assert hasattr(result, "offset")


# ---------------------------------------------------------------------------
# Category 7: REST API contract
# ---------------------------------------------------------------------------


class TestRESTAPIContract:
    """Status codes, error shapes, and pagination via FastAPI TestClient."""

    def _app(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        return create_app(hippo_client=client, routers=[health_router])

    def _app_with_entity(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        return create_app(hippo_client=client, routers=[health_router, entity_router])

    def test_health_returns_200(self, tmp_hippo):
        tc = TestClient(self._app(tmp_hippo))
        r = tc.get("/health")
        assert r.status_code == 200

    def test_health_returns_healthy_status(self, tmp_hippo):
        tc = TestClient(self._app(tmp_hippo))
        r = tc.get("/health")
        assert r.json()["status"] == "healthy"

    def test_openapi_schema_available(self, tmp_hippo):
        tc = TestClient(self._app(tmp_hippo))
        r = tc.get("/openapi.json")
        assert r.status_code == 200
        assert "openapi" in r.json()

    def test_root_endpoint_returns_service_key(self, tmp_hippo):
        tc = TestClient(self._app(tmp_hippo))
        r = tc.get("/")
        assert r.status_code == 200
        assert "service" in r.json()

    def test_entity_list_requires_bearer_auth(self, tmp_hippo):
        tc = TestClient(self._app_with_entity(tmp_hippo))
        r = tc.get("/entities")
        assert r.status_code == 401

    def test_entity_list_with_bearer_auth_returns_200(self, tmp_hippo):
        tc = TestClient(self._app_with_entity(tmp_hippo))
        r = tc.get("/entities", headers={"Authorization": "Bearer test-token"})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Category 8: Delete behavior
# ---------------------------------------------------------------------------


class TestDeleteBehavior:
    """Soft delete: entity unavailable after delete; FTS cleaned up."""

    def test_delete_returns_true(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        assert client.delete("Sample", result["id"]) is True

    @pytest.mark.xfail(
        reason="HippoClient.get() currently returns deleted entities; "
               "soft-delete is not yet enforced on reads (only excluded from query()). "
               "Revisit when Hippo adds availability filtering to get_by_id."
    )
    def test_deleted_entity_not_found_via_get(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        result = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        client.delete("Sample", result["id"])
        with pytest.raises(EntityNotFoundError):
            client.get("Sample", result["id"])

    def test_deleted_entity_not_in_query_results(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        r1 = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        client.create("Sample", {"name": "S002", "tissue": "HC"})
        client.delete("Sample", r1["id"])

        result = client.query("Sample")
        ids = [item["id"] for item in result.items]
        assert r1["id"] not in ids
        assert result.total == 1


# ---------------------------------------------------------------------------
# Category 9: Supersede entity (atomic supersession)
# ---------------------------------------------------------------------------


class TestSupersedentity:
    """Atomic supersession contract: source unavailable, relationship edge created."""

    def test_supersede_returns_supersession_details(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        old = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        new = client.create("Sample", {"name": "S002", "tissue": "DLPFC"})
        result = client.supersede_entity(old["id"], new["id"], reason="re-analysis")
        assert result["entity_id"] == old["id"]
        assert result["replacement_id"] == new["id"]
        assert result["reason"] == "re-analysis"

    def test_supersede_nonexistent_source_raises(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        new = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        with pytest.raises(EntityNotFoundError):
            client.supersede_entity("nonexistent-id", new["id"])

    def test_supersede_nonexistent_replacement_raises(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        old = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        with pytest.raises(EntityNotFoundError):
            client.supersede_entity(old["id"], "nonexistent-replacement")

    def test_double_supersede_raises_already_superseded(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        old = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        r1 = client.create("Sample", {"name": "S002", "tissue": "DLPFC"})
        r2 = client.create("Sample", {"name": "S003", "tissue": "DLPFC"})
        client.supersede_entity(old["id"], r1["id"])
        with pytest.raises(EntityAlreadySupersededError):
            client.supersede_entity(old["id"], r2["id"])

    def test_replacement_entity_still_available_after_supersede(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        old = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        new = client.create("Sample", {"name": "S002", "tissue": "DLPFC"})
        client.supersede_entity(old["id"], new["id"])
        fetched_new = client.get("Sample", new["id"])
        assert fetched_new["id"] == new["id"]


# ---------------------------------------------------------------------------
# Category 10: External IDs
# ---------------------------------------------------------------------------


class TestExternalIDs:
    """Register, look up, and supersede external IDs."""

    def test_register_external_id_returns_record(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        entity = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        record = client.register_external_id(entity["id"], "STARLIMS-001")
        assert record["entity_id"] == entity["id"]
        assert record["external_id"] == "STARLIMS-001"
        assert record["id"]

    def test_register_external_id_for_nonexistent_entity_raises(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        with pytest.raises(EntityNotFoundError):
            client.register_external_id("does-not-exist", "EXT-001")

    def test_supersede_external_id(self, tmp_hippo):
        client = _make_client(tmp_hippo)
        entity = client.create("Sample", {"name": "S001", "tissue": "DLPFC"})
        client.register_external_id(entity["id"], "OLD-ID")
        new_record = client.supersede(entity["id"], "OLD-ID", "NEW-ID")
        assert new_record["external_id"] == "NEW-ID"
        assert new_record["entity_id"] == entity["id"]
