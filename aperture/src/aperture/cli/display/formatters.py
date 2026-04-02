"""Output formatters for table, JSON, and CSV output."""

from __future__ import annotations

import csv
import io
import json
import sys
from typing import Any

from aperture.models.display import ColumnDef, DisplayResult, OutputFormat


def format_output(
    result: DisplayResult,
    fmt: OutputFormat = OutputFormat.TABLE,
    no_color: bool = False,
    file: Any = None,
) -> None:
    """Format and print a DisplayResult in the requested format."""
    out = file or sys.stdout

    if fmt == OutputFormat.JSON:
        _format_json(result, out)
    elif fmt == OutputFormat.CSV:
        _format_csv(result, out)
    else:
        _format_table(result, out, no_color=no_color)


def _format_json(result: DisplayResult, out: Any) -> None:
    """Output data as formatted JSON."""
    json.dump(result.data, out, indent=2, default=str)
    out.write("\n")


def _format_csv(result: DisplayResult, out: Any) -> None:
    """Output data as CSV with header row."""
    if result.is_detail:
        # Single entity: key-value pairs
        rows = [result.data] if isinstance(result.data, dict) else result.data
    elif result.is_list:
        rows = result.data
    else:
        rows = [result.data]

    if not rows:
        return

    # Determine columns
    if result.columns:
        fieldnames = [c.key for c in result.columns]
    else:
        fieldnames = list(rows[0].keys()) if rows else []

    writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def _format_table(result: DisplayResult, out: Any, no_color: bool = False) -> None:
    """Output data as a Rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console(file=out, no_color=no_color, force_terminal=not no_color)

    if result.is_detail and isinstance(result.data, dict):
        # Detail view: 2-column key/value
        table = Table(
            title=result.title,
            show_header=True,
            header_style="bold" if not no_color else None,
        )
        table.add_column("Field", style="cyan" if not no_color else None)
        table.add_column("Value")
        for key, value in result.data.items():
            table.add_row(str(key), str(value) if value is not None else "")
        console.print(table)
        return

    # List view
    rows = result.data if result.is_list else [result.data]
    if not rows:
        console.print("[dim]No results found.[/dim]" if not no_color else "No results found.")
        return

    table = Table(
        title=result.title,
        show_header=True,
        header_style="bold" if not no_color else None,
    )

    # Determine columns
    if result.columns:
        for col in result.columns:
            table.add_column(
                col.name,
                max_width=col.max_width,
                overflow="ellipsis" if col.max_width else None,
            )
        for row in rows:
            table.add_row(
                *[str(row.get(col.key, "")) for col in result.columns]
            )
    else:
        # Auto-detect columns from first row
        columns = list(rows[0].keys())
        for col_name in columns:
            table.add_column(col_name)
        for row in rows:
            table.add_row(*[str(row.get(c, "")) for c in columns])

    console.print(table)


def auto_columns(data: list[dict], entity_type: str | None = None) -> list[ColumnDef]:
    """Generate default column definitions from data."""
    if not data:
        return []

    # Default priority columns
    priority = ["id", "name", "entity_type", "status", "is_available", "created_at", "updated_at"]
    keys = list(data[0].keys())

    ordered = [k for k in priority if k in keys]
    ordered.extend(k for k in keys if k not in ordered)

    return [ColumnDef(name=k, key=k, max_width=60) for k in ordered[:10]]
