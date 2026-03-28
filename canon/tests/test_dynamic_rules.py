"""Tests for dynamic rule registration — DynamicRuleStore, RuleRegistry, and REST endpoint."""

from __future__ import annotations

import pytest

from canon.rules.dynamic_store import DynamicProducesSpec, DynamicRule, DynamicRuleStore
from canon.rules.models import ProductionRule, ProducesSpec, ExecuteSpec
from canon.rules.registry import RuleRegistry


# ---------------------------------------------------------------------------
# DynamicRule dataclass
# ---------------------------------------------------------------------------

def _make_dynamic_rule(name="deseq2-contrast", cwl_url="https://example.com/deseq2.cwl"):
    return DynamicRule(
        name=name,
        description="DESeq2 differential expression",
        produces=[
            DynamicProducesSpec(
                entity_type="DifferentialExpression",
                from_output="result",
                match={"contrast": "{contrast}"},
            )
        ],
        requires=['CountsMatrix{id: "{counts_matrix_id}"}'],
        cwl_url=cwl_url,
        tags=["rnaseq", "deseq2"],
    )


def test_dynamic_rule_fields():
    rule = _make_dynamic_rule()
    assert rule.name == "deseq2-contrast"
    assert rule.cwl_url == "https://example.com/deseq2.cwl"
    assert len(rule.produces) == 1
    assert rule.produces[0].entity_type == "DifferentialExpression"
    assert rule.produces[0].from_output == "result"
    assert rule.produces[0].match == {"contrast": "{contrast}"}
    assert rule.requires == ['CountsMatrix{id: "{counts_matrix_id}"}']
    assert "rnaseq" in rule.tags


def test_dynamic_rule_default_tags():
    rule = DynamicRule(
        name="r",
        description="",
        produces=[],
        requires=[],
        cwl_url="https://example.com/tool.cwl",
    )
    assert rule.tags == []


def test_dynamic_produces_spec_from_output_optional():
    spec = DynamicProducesSpec(entity_type="Foo", match={})
    assert spec.from_output is None


# ---------------------------------------------------------------------------
# DynamicRuleStore
# ---------------------------------------------------------------------------

def test_dynamic_rule_store_register_and_get():
    store = DynamicRuleStore()
    rule = _make_dynamic_rule()
    store.register(rule)
    assert store.get("deseq2-contrast") is rule


def test_dynamic_rule_store_get_unknown_returns_none():
    store = DynamicRuleStore()
    assert store.get("nonexistent") is None


def test_dynamic_rule_store_has_name_true():
    store = DynamicRuleStore()
    store.register(_make_dynamic_rule())
    assert store.has_name("deseq2-contrast") is True


def test_dynamic_rule_store_has_name_false():
    store = DynamicRuleStore()
    assert store.has_name("no-such-rule") is False


def test_dynamic_rule_store_duplicate_name_raises():
    store = DynamicRuleStore()
    store.register(_make_dynamic_rule())
    with pytest.raises(ValueError, match="already registered"):
        store.register(_make_dynamic_rule())


def test_dynamic_rule_store_all_rules_empty():
    store = DynamicRuleStore()
    assert store.all_rules() == []


def test_dynamic_rule_store_all_rules_returns_all():
    store = DynamicRuleStore()
    r1 = _make_dynamic_rule("rule-a")
    r2 = _make_dynamic_rule("rule-b")
    store.register(r1)
    store.register(r2)
    all_rules = store.all_rules()
    assert len(all_rules) == 2
    assert {r.name for r in all_rules} == {"rule-a", "rule-b"}


def test_dynamic_rule_store_len():
    store = DynamicRuleStore()
    assert len(store) == 0
    store.register(_make_dynamic_rule("r1"))
    assert len(store) == 1
    store.register(_make_dynamic_rule("r2"))
    assert len(store) == 2


# ---------------------------------------------------------------------------
# RuleRegistry.find_dynamic_rule()
# ---------------------------------------------------------------------------

def test_rule_registry_find_dynamic_rule_no_store():
    registry = RuleRegistry([])
    assert registry.find_dynamic_rule("any-name") is None


def test_rule_registry_find_dynamic_rule_found():
    store = DynamicRuleStore()
    rule = _make_dynamic_rule()
    store.register(rule)

    registry = RuleRegistry([], dynamic_store=store)
    assert registry.find_dynamic_rule("deseq2-contrast") is rule


def test_rule_registry_find_dynamic_rule_not_found():
    store = DynamicRuleStore()
    registry = RuleRegistry([], dynamic_store=store)
    assert registry.find_dynamic_rule("nonexistent") is None


def test_rule_registry_set_dynamic_store():
    registry = RuleRegistry([])
    assert registry.find_dynamic_rule("r") is None

    store = DynamicRuleStore()
    store.register(_make_dynamic_rule())
    registry.set_dynamic_store(store)

    assert registry.find_dynamic_rule("deseq2-contrast") is not None


def test_rule_registry_dynamic_store_independent_of_static_rules():
    """Static rules and dynamic rules coexist without interference."""
    static = ProductionRule(
        name="static-rule",
        description="",
        produces=ProducesSpec(entity_type="AlignedReads", match={"sample": "{sample}"}),
        requires=[],
        execute=ExecuteSpec(workflow="w.cwl", inputs={}),
    )
    store = DynamicRuleStore()
    store.register(_make_dynamic_rule())

    registry = RuleRegistry([static], dynamic_store=store)

    assert registry.get_rule("static-rule") is static
    assert registry.find_dynamic_rule("deseq2-contrast") is not None
    assert registry.find_dynamic_rule("static-rule") is None  # not in dynamic store


# ---------------------------------------------------------------------------
# REST endpoint — POST /api/v1/rules
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Return a FastAPI TestClient with a fresh DynamicRuleStore."""
    from fastapi.testclient import TestClient
    from canon.api.app import app
    from canon.api.rules import get_rule_store

    fresh_store = DynamicRuleStore()
    app.dependency_overrides[get_rule_store] = lambda: fresh_store
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


_VALID_PAYLOAD = {
    "name": "deseq2-contrast",
    "produces": [
        {
            "entity_type": "DifferentialExpression",
            "from_output": "result",
            "match": {"contrast": "{contrast}"},
        }
    ],
    "requires": [{"ref": 'CountsMatrix{id: "{counts_matrix_id}"}'}],
    "execute": {"cwl_url": "https://example.com/deseq2.cwl"},
    "description": "DESeq2 differential expression analysis",
    "tags": ["rnaseq", "deseq2"],
}


def test_endpoint_register_rule_success(api_client):
    response = api_client.post("/api/v1/rules", json=_VALID_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "deseq2-contrast"
    assert data["status"] == "registered"


def test_endpoint_register_rule_duplicate_name_returns_409(api_client):
    api_client.post("/api/v1/rules", json=_VALID_PAYLOAD)
    response = api_client.post("/api/v1/rules", json=_VALID_PAYLOAD)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_endpoint_register_rule_missing_execute_returns_422(api_client):
    payload = {**_VALID_PAYLOAD}
    del payload["execute"]
    response = api_client.post("/api/v1/rules", json=payload)
    assert response.status_code == 422


def test_endpoint_register_rule_empty_produces_returns_422(api_client):
    payload = {**_VALID_PAYLOAD, "produces": []}
    response = api_client.post("/api/v1/rules", json=payload)
    assert response.status_code == 422


def test_endpoint_register_rule_missing_name_returns_422(api_client):
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "name"}
    response = api_client.post("/api/v1/rules", json=payload)
    assert response.status_code == 422


def test_endpoint_optional_fields_have_defaults(api_client):
    """description and tags are optional; requires defaults to []."""
    payload = {
        "name": "minimal-rule",
        "produces": [{"entity_type": "AlignedReads", "match": {}}],
        "execute": {"cwl_url": "https://example.com/align.cwl"},
    }
    response = api_client.post("/api/v1/rules", json=payload)
    assert response.status_code == 201


def test_endpoint_entity_type_validator_reject(api_client):
    """When the entity_type_validator returns False, the endpoint returns 422."""
    from canon.api.rules import get_entity_type_validator
    from canon.api.app import app

    app.dependency_overrides[get_entity_type_validator] = lambda: (lambda et: False)
    try:
        response = api_client.post("/api/v1/rules", json=_VALID_PAYLOAD)
        assert response.status_code == 422
        assert "not found in Hippo schema" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_entity_type_validator, None)


def test_endpoint_rule_stored_in_store(api_client):
    """After a successful POST, the rule exists in the injected store."""
    fresh_store = DynamicRuleStore()
    from canon.api.app import app
    from canon.api.rules import get_rule_store
    app.dependency_overrides[get_rule_store] = lambda: fresh_store

    api_client.post("/api/v1/rules", json=_VALID_PAYLOAD)

    rule = fresh_store.get("deseq2-contrast")
    assert rule is not None
    assert rule.cwl_url == "https://example.com/deseq2.cwl"
    assert len(rule.produces) == 1
    assert rule.produces[0].entity_type == "DifferentialExpression"
    assert rule.requires == ['CountsMatrix{id: "{counts_matrix_id}"}']
    assert rule.tags == ["rnaseq", "deseq2"]
