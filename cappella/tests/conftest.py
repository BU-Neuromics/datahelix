"""Shared fixtures for Cappella tests."""
import pytest

from cappella.canon.client import CanonClient, CanonDecision
from cappella.config import CappellaConfig
from cappella.resolver.traversal import HippoClientProtocol


class MockHippoClient:
    """Mock Hippo client for testing."""

    def __init__(self, entities: dict | None = None) -> None:
        # entities: dict mapping entity_type -> list of entity dicts
        self._entities: dict[str, list[dict]] = entities or {}
        self._schema_refs: dict[str, list[str]] = {}

    def set_schema_references(self, entity_type: str, refs: list[str]) -> None:
        self._schema_refs[entity_type] = refs

    def schema_references(self, entity_type: str) -> list[str]:
        return self._schema_refs.get(entity_type, [])

    def query(self, entity_type: str, filters: dict) -> list[dict]:
        entities = self._entities.get(entity_type, [])
        if not filters or filters == {}:
            return list(entities)
        # Apply simple filter matching
        result = []
        for entity in entities:
            match = True
            for k, v in filters.items():
                if k == "check" and v == "missing":
                    # Return entities with _missing flag
                    if not entity.get("_missing"):
                        match = False
                        break
                elif entity.get(k) != v:
                    match = False
                    break
            if match:
                result.append(entity)
        return result

    def get_by_external_id(self, system: str, external_id: str) -> dict | None:
        for entity_list in self._entities.values():
            for entity in entity_list:
                if entity.get("external_id") == external_id and entity.get("source_system") == system:
                    return entity
        return None

    def create(self, entity_type: str, data: dict, context: dict) -> dict:
        entity = {"id": f"new-{len(self._entities.get(entity_type, []))}", **data}
        if entity_type not in self._entities:
            self._entities[entity_type] = []
        self._entities[entity_type].append(entity)
        return entity

    def update(self, entity_id: str, data: dict, context: dict) -> dict:
        for entity_list in self._entities.values():
            for entity in entity_list:
                if entity.get("id") == entity_id:
                    entity.update(data)
                    return entity
        return {**data, "id": entity_id}


def make_mock_canon_client(decision: str = "REUSE", uri: str | None = "uri://sample/1") -> CanonClient:
    """Create a CanonClient with a stub that returns the given decision."""
    def stub(entity_type: str, params: dict) -> CanonDecision:
        return CanonDecision(decision=decision, uri=uri)

    return CanonClient(stub=stub)


@pytest.fixture
def mock_hippo() -> MockHippoClient:
    return MockHippoClient()


@pytest.fixture
def mock_canon() -> CanonClient:
    return make_mock_canon_client()


@pytest.fixture
def sample_config() -> CappellaConfig:
    return CappellaConfig()


@pytest.fixture
def sample_csv_data() -> bytes:
    return b"id,name,species\n1,Sample_A,human\n2,Sample_B,mouse\n"


@pytest.fixture
def sample_json_data() -> bytes:
    import json
    data = {"data": {"scores": [{"id": "s1", "score": 95}, {"id": "s2", "score": 88}]}}
    return json.dumps(data).encode()


@pytest.fixture
def sample_xml_data() -> bytes:
    return b"""<?xml version="1.0"?>
<root>
  <record record_id="r1">
    <name>Alpha</name>
    <status>active</status>
  </record>
  <record record_id="r2">
    <name>Beta</name>
    <status>inactive</status>
  </record>
</root>
"""
