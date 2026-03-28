"""Rule model dataclasses for Canon's production rule system."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Regex to detect a pure wildcard: exactly "{name}"
_PURE_WILDCARD_RE = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)\}$")
# Regex to detect an entity reference string
_ENTITY_REF_RE = re.compile(r"^ref:([A-Za-z][A-Za-z0-9_]*)(\{.*\})$")

# v0.2 decision: use simple "*" glob wildcards for partial specification matching
# instead of full CEL expressions. CEL predicates on match fields deferred to v0.3.


def is_pure_wildcard(value: Any) -> bool:
    """Return True if value is a string matching exactly {name}."""
    return isinstance(value, str) and bool(_PURE_WILDCARD_RE.match(value))


def is_glob_wildcard(value: Any) -> bool:
    """Return True if value is the glob wildcard sentinel "*".

    A glob wildcard in a rule's produces.match means "accept any value for this
    field, including fields the caller did not specify". This enables partial
    specification matching: callers need not provide every identity field.

    Example rule YAML::

        match:
          sample_id: "{sample_id}"   # exact, from request params
          genome: "{genome}"         # exact, from request params
          tool_version: "*"          # any value accepted — caller may omit this
    """
    return value == "*"


def extract_wildcard_name(value: str) -> str:
    """Extract the name from a pure wildcard expression like {sample} → sample."""
    m = _PURE_WILDCARD_RE.match(value)
    if not m:
        raise ValueError(f"Not a pure wildcard: {value!r}")
    return m.group(1)


def is_entity_ref(value: Any) -> bool:
    """Return True if value is an entity reference string (ref:Type{...})."""
    return isinstance(value, str) and bool(_ENTITY_REF_RE.match(value))


@dataclass
class ProducesSpec:
    """Describes what a rule produces: entity type + identity parameters."""

    entity_type: str
    match: dict[str, Any]  # param → scalar, entity ref string, or wildcard string


@dataclass
class InputBinding:
    """A required input that must be resolved before execution."""

    bind: str       # name used in execute.inputs expressions
    entity_type: str
    match: dict[str, Any]  # param → scalar, entity ref, or wildcard


@dataclass
class ExecuteSpec:
    """CWL execution specification for a rule."""

    workflow: str              # relative path to .cwl file
    inputs: dict[str, Any]    # CWL input name → value expression


@dataclass
class ProductionRule:
    """A complete Canon production rule."""

    name: str
    description: str
    produces: ProducesSpec
    requires: list[InputBinding]
    execute: ExecuteSpec


@dataclass
class FetchRule:
    """A Canon fetch rule — materialize an entity by downloading from a URI."""

    name: str
    produces: ProducesSpec
    source_uri: str
    checksum_sha256: str | None = None
