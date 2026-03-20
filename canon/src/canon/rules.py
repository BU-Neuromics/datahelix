"""Pydantic models for Canon production rules."""

from __future__ import annotations

import re

from pydantic import BaseModel


def extract_wildcards(s: str) -> set[str]:
    """Return all {name} placeholder names found in *s*."""
    return set(re.findall(r'\{(\w+)\}', s))


class OutputSpec(BaseModel):
    """Describes an entity produced by a workflow execution."""

    bind: str
    entity_type: str
    pattern: str


class InputBinding(BaseModel):
    """Describes a required input entity for a rule."""

    bind: str
    entity_type: str
    resolve: str = 'uri'
    metadata: dict[str, str] = {}


class ProducesSpec(BaseModel):
    """Describes the entity type and metadata a rule produces."""

    entity_type: str
    metadata: dict[str, str] = {}


class ExecuteSpec(BaseModel):
    """Describes the workflow to execute and how to wire inputs/outputs."""

    workflow: str
    inputs: dict[str, str] = {}
    outputs: list[OutputSpec] = []


class ProductionRule(BaseModel):
    """A named rule that describes how to produce an entity."""

    name: str
    produces: ProducesSpec
    requires: list[InputBinding] = []
    execute: ExecuteSpec

    @property
    def wildcard_names(self) -> set[str]:
        """All {name} placeholders found in produces.metadata and requires[*].metadata."""
        names: set[str] = set()
        for value in self.produces.metadata.values():
            names |= extract_wildcards(value)
        for binding in self.requires:
            for value in binding.metadata.values():
                names |= extract_wildcards(value)
        return names
