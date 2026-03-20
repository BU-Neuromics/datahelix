"""Tests for wildcard resolution."""

from __future__ import annotations

import pytest

from canon.exceptions import CanonPlanningError
from canon.resolver import resolve_wildcards
from canon.rules import ProductionRule
from canon.types import WildcardBinding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rule(name: str, produces_metadata: dict, requires: list[dict] | None = None) -> ProductionRule:
    d = {
        "name": name,
        "produces": {
            "entity_type": "Foo",
            "metadata": produces_metadata,
        },
        "requires": requires or [],
        "execute": {
            "workflow": name,
            "inputs": {},
            "outputs": [],
        },
    }
    return ProductionRule.model_validate(d)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_wildcards_from_request_spec():
    rule = _rule("r", {"genome_build": "{genome_build}", "sample_id": "{sample_id}"})
    binding = resolve_wildcards(
        rule,
        request_spec={"genome_build": "GRCh38", "sample_id": "S001"},
        input_entities={},
    )
    assert binding["genome_build"] == "GRCh38"
    assert binding["sample_id"] == "S001"


def test_resolve_wildcards_from_input_entity_field():
    rule = _rule("r", {"genome_build": "{genome_build}"})
    binding = resolve_wildcards(
        rule,
        request_spec={},
        input_entities={"ref": {"genome_build": "GRCh38", "uri": "file:///idx"}},
    )
    assert binding["genome_build"] == "GRCh38"


def test_request_spec_takes_precedence_over_entity_fields():
    rule = _rule("r", {"genome_build": "{genome_build}"})
    binding = resolve_wildcards(
        rule,
        request_spec={"genome_build": "hg19"},
        input_entities={"ref": {"genome_build": "GRCh38"}},
    )
    assert binding["genome_build"] == "hg19"


def test_unbound_required_wildcard_raises_planning_error():
    rule = _rule(
        "r",
        {"genome_build": "{genome_build}", "missing_field": "{missing_field}"},
    )
    with pytest.raises(CanonPlanningError, match="missing_field"):
        resolve_wildcards(
            rule,
            request_spec={"genome_build": "GRCh38"},
            input_entities={},
        )
