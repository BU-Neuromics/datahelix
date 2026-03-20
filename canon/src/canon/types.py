"""Shared types and value resolvers for Canon."""

from __future__ import annotations

import json
from typing import Iterator, TypedDict

from canon.exceptions import CanonValidationError

# ---------------------------------------------------------------------------
# Simple type aliases
# ---------------------------------------------------------------------------

MetadataSpec = dict[str, str]


# ---------------------------------------------------------------------------
# WildcardBinding
# ---------------------------------------------------------------------------

class WildcardBinding:
    """Maps wildcard names to resolved string values."""

    def __init__(self, data: dict[str, str] | None = None) -> None:
        self._data: dict[str, str] = dict(data) if data else {}

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> str:
        return self._data[key]

    def __setitem__(self, key: str, value: str) -> None:
        self._data[key] = value

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def items(self) -> Iterator[tuple[str, str]]:
        return iter(self._data.items())

    def __repr__(self) -> str:
        return f"WildcardBinding({self._data!r})"

    def as_dict(self) -> dict[str, str]:
        return dict(self._data)


# ---------------------------------------------------------------------------
# ResolvedInput
# ---------------------------------------------------------------------------

class ResolvedInput(TypedDict):
    bind: str
    entity_type: str
    entity: dict


# ---------------------------------------------------------------------------
# Value resolvers
# ---------------------------------------------------------------------------

class URIResolver:
    """Resolves to the entity's 'uri' field."""

    def resolve(self, entity: dict) -> str:
        try:
            return entity['uri']
        except KeyError:
            raise CanonValidationError("Entity is missing required field 'uri'")


class FieldResolver:
    """Resolves to a named field on the entity."""

    def __init__(self, field: str) -> None:
        self.field = field

    def resolve(self, entity: dict) -> str:
        try:
            return entity[self.field]
        except KeyError:
            raise CanonValidationError(
                f"Entity is missing required field '{self.field}'"
            )


class InlineResolver:
    """Always resolves to a fixed inline value."""

    def __init__(self, value: str) -> None:
        self.value = value

    def resolve(self, entity: dict) -> str:  # noqa: ARG002
        return self.value


class JSONResolver:
    """Resolves to the JSON-serialised entity."""

    def resolve(self, entity: dict) -> str:
        return json.dumps(entity)


ValueResolverType = URIResolver | FieldResolver | InlineResolver | JSONResolver
