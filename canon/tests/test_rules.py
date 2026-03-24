"""Tests for RulesLoader and RuleRegistry."""

from __future__ import annotations

import yaml
import pytest
from pathlib import Path

from canon.rules.loader import RulesLoader
from canon.rules.registry import RuleRegistry
from canon.rules.models import (
    ProductionRule,
    ProducesSpec,
    InputBinding,
    ExecuteSpec,
    is_pure_wildcard,
    is_entity_ref,
)
from canon.exceptions import CanonRuleValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_rules(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "canon_rules.yaml"
    p.write_text(yaml.dump(data))
    return p


def _make_cwl_and_sidecar(tmp_path: Path, workflow: str = "workflows/star_align.cwl") -> Path:
    """Create a stub CWL file and its sidecar so semantic validation passes."""
    cwl = tmp_path / workflow
    cwl.parent.mkdir(parents=True, exist_ok=True)
    cwl.write_text(
        "#!/usr/bin/env cwltool\nclass: CommandLineTool\ncwlVersion: v1.2\nbaseCommand: echo\n"
    )
    sidecar = cwl.with_name(cwl.stem + ".canon.yaml")
    sidecar.write_text(
        "outputs:\n"
        "  aligned_bam:\n"
        "    entity_type: AlignedReads\n"
        "    identity_fields: [sample]\n"
        "    hippo_fields:\n"
        "      uri: '{outputs.bam.location}'\n"
    )
    return cwl


# ---------------------------------------------------------------------------
# RulesLoader
# ---------------------------------------------------------------------------

def test_valid_rules_parse(tmp_path):
    _make_cwl_and_sidecar(tmp_path, "workflows/star_align.cwl")
    data = {
        "rules": [
            {
                "name": "align-reads",
                "description": "Align with STAR",
                "produces": {
                    "entity_type": "AlignedReads",
                    "match": {"sample": "{sample}", "genome_build": "{genome_build}"},
                },
                "requires": [
                    {"bind": "reads", "entity_type": "RawReads", "match": {"sample": "{sample}"}}
                ],
                "execute": {
                    "workflow": "workflows/star_align.cwl",
                    "inputs": {"reads_fastq": "{reads.uri}", "genome_build": "{genome_build}"},
                },
            }
        ]
    }
    p = _write_rules(tmp_path, data)
    loader = RulesLoader(p)
    rules = loader.load()
    assert len(rules) == 1
    assert rules[0].name == "align-reads"
    assert rules[0].produces.entity_type == "AlignedReads"
    assert rules[0].produces.match["sample"] == "{sample}"
    assert len(rules[0].requires) == 1
    assert rules[0].requires[0].bind == "reads"


def test_duplicate_rule_names_raise(tmp_path):
    data = {
        "rules": [
            {
                "name": "my-rule",
                "produces": {"entity_type": "Foo", "match": {"x": "1"}},
                "execute": {"workflow": "w.cwl", "inputs": {}},
            },
            {
                "name": "my-rule",
                "produces": {"entity_type": "Foo", "match": {"x": "2"}},
                "execute": {"workflow": "w.cwl", "inputs": {}},
            },
        ]
    }
    p = _write_rules(tmp_path, data)
    with pytest.raises(CanonRuleValidationError, match="my-rule"):
        RulesLoader(p).load()


def test_missing_name_raises(tmp_path):
    data = {
        "rules": [
            {
                "produces": {"entity_type": "Foo", "match": {}},
                "execute": {"workflow": "w.cwl", "inputs": {}},
            }
        ]
    }
    p = _write_rules(tmp_path, data)
    with pytest.raises(CanonRuleValidationError):
        RulesLoader(p).load()


def test_missing_produces_raises(tmp_path):
    data = {
        "rules": [
            {
                "name": "bad-rule",
                "execute": {"workflow": "w.cwl", "inputs": {}},
            }
        ]
    }
    p = _write_rules(tmp_path, data)
    with pytest.raises(CanonRuleValidationError):
        RulesLoader(p).load()


# ---------------------------------------------------------------------------
# is_pure_wildcard
# ---------------------------------------------------------------------------

def test_is_pure_wildcard_true():
    assert is_pure_wildcard("{sample}") is True
    assert is_pure_wildcard("{genome_build}") is True
    assert is_pure_wildcard("{x}") is True


def test_is_pure_wildcard_false():
    assert is_pure_wildcard("plain_value") is False
    assert is_pure_wildcard("ref:ToolVersion{name=STAR}") is False
    assert is_pure_wildcard("{sample}_extra") is False
    assert is_pure_wildcard("") is False
    assert is_pure_wildcard(42) is False
    assert is_pure_wildcard("{a}{b}") is False


# ---------------------------------------------------------------------------
# RuleRegistry
# ---------------------------------------------------------------------------

def _make_rule(name, entity_type, match, requires=None):
    return ProductionRule(
        name=name,
        description="",
        produces=ProducesSpec(entity_type=entity_type, match=match),
        requires=requires or [],
        execute=ExecuteSpec(workflow="w.cwl", inputs={}),
    )


def test_registry_wildcard_matches_any_value():
    rule = _make_rule("r", "AlignedReads", {"sample": "{sample}"})
    registry = RuleRegistry([rule])
    assert registry.find_rule("AlignedReads", {"sample": "S001"}) is rule
    assert registry.find_rule("AlignedReads", {"sample": "ANYTHINGELSE"}) is rule


def test_registry_fixed_param_must_match_exactly():
    rule = _make_rule("r", "AlignedReads", {"genome_build": "GRCh38"})
    registry = RuleRegistry([rule])
    assert registry.find_rule("AlignedReads", {"genome_build": "GRCh38"}) is rule
    assert registry.find_rule("AlignedReads", {"genome_build": "GRCh37"}) is None
    assert registry.find_rule("AlignedReads", {}) is None


def test_registry_rules_for_entity_type():
    r1 = _make_rule("r1", "AlignedReads", {})
    r2 = _make_rule("r2", "GeneAnnotation", {})
    r3 = _make_rule("r3", "AlignedReads", {"tool": "bowtie"})
    registry = RuleRegistry([r1, r2, r3])
    aligned = registry.rules_for_entity_type("AlignedReads")
    assert len(aligned) == 2
    assert {x.name for x in aligned} == {"r1", "r3"}
    assert registry.rules_for_entity_type("GeneAnnotation") == [r2]
    assert registry.rules_for_entity_type("Unknown") == []


def test_registry_wrong_entity_type_never_matches():
    rule = _make_rule("r", "AlignedReads", {"sample": "{sample}"})
    registry = RuleRegistry([rule])
    assert registry.find_rule("GeneAnnotation", {"sample": "S001"}) is None


def test_entity_ref_in_rules_is_detected():
    rule = _make_rule("r", "AlignedReads", {"tool_version": "ref:ToolVersion{version=2.7.11a}"})
    assert is_entity_ref(rule.produces.match["tool_version"]) is True
    assert is_entity_ref(rule.produces.match.get("other", "plain")) is False
