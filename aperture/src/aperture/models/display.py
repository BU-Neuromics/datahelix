"""Display models for CLI output."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    CSV = "csv"


@dataclass
class ColumnDef:
    name: str
    key: str
    max_width: int | None = None


@dataclass
class DisplayResult:
    """Standardized container for data to be formatted and displayed."""

    data: list[dict[str, Any]] | dict[str, Any]
    columns: list[ColumnDef] = field(default_factory=list)
    title: str | None = None
    is_detail: bool = False

    @property
    def is_list(self) -> bool:
        return isinstance(self.data, list)
