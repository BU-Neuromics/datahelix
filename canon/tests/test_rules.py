"""Tests for ProductionRule, RulesLoader, and RulesEngine."""

from __future__ import annotations

import pytest
import yaml

from canon.exceptions import CanonValidationError
from canon.rule_loader import RulesLoader
from canon.rule_registry import RulesEngine
from canon.rules import ProductionRule, extract_wildcards


# ---------------------------------------------------------------------------
# ProductionRule
# ---------------------------------------------------------------------------


def test_production_rule_loads_from_valid_dict(sample_rule_dict):
    rule = ProductionRule.model_validate(sample_rule_dict)
    assert rule.name == "align-with-star"
    assert rule.produces.entity_type == "AlignmentFile"
    assert len(rule.requires) == 2
    assert rule.execute.workflow == "star_align"


def test_wildcard_names_extracts_all_placeholders(sample_rule_dict):
    rule = ProductionRule.model_validate(sample_rule_dict)
    wn = rule.wildcard_names
    assert "genome_build" in wn
    assert "sample_id" in wn


def test_malformed_wildcard_not_extracted():
    # {bad (no closing brace) — regex \{(\w+)\} won't match
    names = extract_wildcards("prefix_{bad and more text")
    assert "bad" not in names


def test_duplicate_wildcard_names_deduplicated():
    rule_dict = {
        "name": "test-rule",
        "produces": {
            "entity_type": "Foo",
            "metadata": {"a": "{x}", "b": "{x}"},
        },
        "execute": {
            "workflow": "foo",
            "inputs": {"K": "{x}"},
            "outputs": [],
        },
    }
    rule = ProductionRule.model_validate(rule_dict)
    assert rule.wildcard_names == {"x"}


# ---------------------------------------------------------------------------
# RulesLoader
# ---------------------------------------------------------------------------


def test_rules_loader_from_file_loads_three_rules(sample_rules_yaml):
    loader = RulesLoader.from_file(sample_rules_yaml)
    assert len(loader.rules) == 3


def test_rules_loader_raises_on_missing_file():
    with pytest.raises(CanonValidationError, match="not found"):
        RulesLoader.from_file("/nonexistent/path/canon_rules.yaml")


def test_rules_loader_missing_file_includes_path_in_error():
    path = "/nonexistent/path/canon_rules.yaml"
    with pytest.raises(CanonValidationError, match=path):
        RulesLoader.from_file(path)


def test_rules_loader_collects_all_errors(tmp_path):
    """Two invalid rules (missing 'execute') — both names should appear in the error."""
    rules = [
        {"name": "bad1", "produces": {"entity_type": "Foo"}},
        {"name": "bad2", "produces": {"entity_type": "Bar"}},
    ]
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.dump(rules))
    with pytest.raises(CanonValidationError) as exc_info:
        RulesLoader.from_file(path)
    msg = str(exc_info.value)
    assert "bad1" in msg
    assert "bad2" in msg


# ---------------------------------------------------------------------------
# RulesEngine
# ---------------------------------------------------------------------------


def test_rules_engine_find_rules_returns_matching(sample_rules_yaml):
    loader = RulesLoader.from_file(sample_rules_yaml)
    engine = RulesEngine(loader.rules)
    rules = engine.find_rules("AlignmentFile")
    assert len(rules) == 1
    assert rules[0].name == "align-with-star"


def test_rules_engine_find_rules_returns_empty_for_unknown_type(sample_rules_yaml):
    loader = RulesLoader.from_file(sample_rules_yaml)
    engine = RulesEngine(loader.rules)
    assert engine.find_rules("NonExistentEntityType") == []


def test_rules_engine_validate_raises_on_duplicate_names(sample_rule_dict):
    rule1 = ProductionRule.model_validate(sample_rule_dict)
    rule2 = ProductionRule.model_validate(sample_rule_dict)  # same name
    engine = RulesEngine([rule1, rule2])
    with pytest.raises(CanonValidationError, match="align-with-star"):
        engine.validate()
