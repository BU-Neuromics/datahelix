"""Tests for EntityRefResolver."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from canon.resolver.entity_ref import parse_entity_ref, EntityRefResolver
from canon.types import Entity
from canon.exceptions import CanonResolutionError, CanonPlanningError


# ---------------------------------------------------------------------------
# parse_entity_ref
# ---------------------------------------------------------------------------

def test_parse_ref_expr_simple():
    ref = parse_entity_ref("ref:ToolVersion{version=2.7.11a}")
    assert ref.entity_type == "ToolVersion"
    assert ref.constraints == {"version": "2.7.11a"}


def test_parse_ref_expr_multiple_fields():
    ref = parse_entity_ref("ref:ToolVersion{tool.name=STAR, version=2.7.11a}")
    assert ref.entity_type == "ToolVersion"
    assert ref.constraints["tool.name"] == "STAR"
    assert ref.constraints["version"] == "2.7.11a"


def test_parse_ref_expr_with_nested_braces_raises():
    # parse_entity_ref uses [^}]* which cannot match nested braces like {genome_build}
    with pytest.raises(CanonPlanningError):
        parse_entity_ref("ref:GenomeBuild{name={genome_build}}")


def test_parse_invalid_ref_raises():
    with pytest.raises(CanonPlanningError):
        parse_entity_ref("not-a-ref")


def test_parse_invalid_ref_no_braces_raises():
    with pytest.raises(CanonPlanningError):
        parse_entity_ref("ref:ToolVersion")


# ---------------------------------------------------------------------------
# EntityRefResolver.resolve — success
# ---------------------------------------------------------------------------

def _make_entity(entity_type="ToolVersion", eid="abc-123", data=None):
    return Entity(id=eid, entity_type=entity_type, data=data or {}, uri="/path")


def test_resolve_success():
    hippo = MagicMock()
    entity = _make_entity(eid="abc-123")
    hippo.find_entities.return_value = [entity]
    resolver = EntityRefResolver(hippo)
    result = resolver.resolve("ref:ToolVersion{version=2.7.11a}")
    assert result.id == "abc-123"
    hippo.find_entities.assert_called_once_with("ToolVersion", {"version": "2.7.11a"})


# ---------------------------------------------------------------------------
# EntityRefResolver.resolve — error cases
# ---------------------------------------------------------------------------

def test_resolve_zero_matches_raises():
    hippo = MagicMock()
    hippo.find_entities.return_value = []
    resolver = EntityRefResolver(hippo)
    with pytest.raises(CanonResolutionError):
        resolver.resolve("ref:ToolVersion{version=9.9.9}")


def test_resolve_multiple_matches_raises():
    hippo = MagicMock()
    hippo.find_entities.return_value = [
        _make_entity(eid="id1"),
        _make_entity(eid="id2"),
    ]
    resolver = EntityRefResolver(hippo)
    with pytest.raises(CanonResolutionError, match="Ambiguous"):
        resolver.resolve("ref:ToolVersion{version=2.7.11a}")


# ---------------------------------------------------------------------------
# Wildcard substitution
# ---------------------------------------------------------------------------

def test_wildcard_substitution_bindings_accepted():
    """resolve() accepts bindings even when the ref has no wildcards in its constraints."""
    hippo = MagicMock()
    entity = _make_entity(entity_type="GenomeBuild", eid="gb-uuid", data={"name": "GRCh38"})
    hippo.find_entities.return_value = [entity]
    resolver = EntityRefResolver(hippo)
    # Ref with no wildcards in constraints; bindings are silently unused
    result = resolver.resolve(
        "ref:GenomeBuild{name=GRCh38}",
        bindings={"genome_build": "GRCh38"},
    )
    assert result.id == "gb-uuid"
    hippo.find_entities.assert_called_once_with("GenomeBuild", {"name": "GRCh38"})


def test_substitute_wildcards_function_directly():
    """_substitute_wildcards replaces {name} placeholders from bindings."""
    from canon.resolver.entity_ref import _substitute_wildcards
    result = _substitute_wildcards("hello {sample} world", {"sample": "S001"})
    assert result == "hello S001 world"


def test_substitute_wildcards_unbound_raises():
    """_substitute_wildcards raises CanonPlanningError for unbound wildcards."""
    from canon.resolver.entity_ref import _substitute_wildcards
    with pytest.raises(CanonPlanningError, match="Unbound wildcard"):
        _substitute_wildcards("{missing_wc}", bindings={})


# ---------------------------------------------------------------------------
# Dot-notation constraint handling
# ---------------------------------------------------------------------------

def test_dot_notation_filter_applied_in_memory():
    """tool.name=STAR goes to nested filter; version=x goes to flat Hippo query."""
    hippo = MagicMock()
    entity = _make_entity(
        entity_type="ToolVersion",
        eid="tv-uuid",
        data={"tool": {"name": "STAR"}, "version": "2.7.11a"},
    )
    hippo.find_entities.return_value = [entity]
    resolver = EntityRefResolver(hippo)
    result = resolver.resolve("ref:ToolVersion{tool.name=STAR, version=2.7.11a}")
    # Only flat constraint passed to Hippo
    hippo.find_entities.assert_called_once_with("ToolVersion", {"version": "2.7.11a"})
    assert result.id == "tv-uuid"


def test_dot_notation_filter_excludes_non_matching():
    """Entities that don't satisfy nested filter are excluded."""
    hippo = MagicMock()
    matching = _make_entity(
        entity_type="ToolVersion",
        eid="tv-match",
        data={"tool": {"name": "STAR"}, "version": "2.7.11a"},
    )
    non_matching = _make_entity(
        entity_type="ToolVersion",
        eid="tv-other",
        data={"tool": {"name": "BWA"}, "version": "2.7.11a"},
    )
    hippo.find_entities.return_value = [matching, non_matching]
    resolver = EntityRefResolver(hippo)
    result = resolver.resolve("ref:ToolVersion{tool.name=STAR, version=2.7.11a}")
    assert result.id == "tv-match"
