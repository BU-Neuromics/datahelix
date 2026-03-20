"""Tests for shared types and value resolvers."""

from __future__ import annotations

import json

import pytest

from canon.exceptions import CanonValidationError
from canon.types import (
    FieldResolver,
    InlineResolver,
    JSONResolver,
    URIResolver,
    WildcardBinding,
)


# ---------------------------------------------------------------------------
# WildcardBinding
# ---------------------------------------------------------------------------


def test_wildcard_binding_get():
    wb = WildcardBinding({"a": "1", "b": "2"})
    assert wb.get("a") == "1"
    assert wb.get("z") is None
    assert wb.get("z", "default") == "default"


def test_wildcard_binding_set():
    wb = WildcardBinding()
    wb["x"] = "hello"
    assert wb["x"] == "hello"


def test_wildcard_binding_in():
    wb = WildcardBinding({"k": "v"})
    assert "k" in wb
    assert "z" not in wb


def test_wildcard_binding_getitem():
    wb = WildcardBinding({"k": "v"})
    assert wb["k"] == "v"


# ---------------------------------------------------------------------------
# Value resolvers — happy path
# ---------------------------------------------------------------------------


def test_uri_resolver_returns_entity_uri():
    resolver = URIResolver()
    entity = {"uri": "file:///data/sample.bam", "name": "sample"}
    assert resolver.resolve(entity) == "file:///data/sample.bam"


def test_field_resolver_returns_named_field():
    resolver = FieldResolver("genome_build")
    entity = {"uri": "file:///data/sample.bam", "genome_build": "GRCh38"}
    assert resolver.resolve(entity) == "GRCh38"


def test_inline_resolver_returns_constant():
    resolver = InlineResolver("constant_value")
    assert resolver.resolve({}) == "constant_value"
    assert resolver.resolve({"anything": "ignored"}) == "constant_value"


def test_json_resolver_returns_valid_json_string():
    resolver = JSONResolver()
    entity = {"a": 1, "b": "hello"}
    result = resolver.resolve(entity)
    assert json.loads(result) == entity


# ---------------------------------------------------------------------------
# Value resolvers — error cases
# ---------------------------------------------------------------------------


def test_uri_resolver_raises_on_missing_uri():
    resolver = URIResolver()
    with pytest.raises(CanonValidationError, match="uri"):
        resolver.resolve({"name": "no-uri-here"})


def test_field_resolver_raises_on_missing_field():
    resolver = FieldResolver("genome_build")
    with pytest.raises(CanonValidationError, match="genome_build"):
        resolver.resolve({"uri": "file:///x"})
