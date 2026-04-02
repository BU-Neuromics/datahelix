"""Provenance/history command."""

from __future__ import annotations

from typing import Annotated

import typer

from aperture.cli.display.formatters import format_output
from aperture.models.display import ColumnDef, DisplayResult, OutputFormat

provenance_app = typer.Typer()

HISTORY_COLUMNS = [
    ColumnDef(name="event_type", key="event_type"),
    ColumnDef(name="actor", key="actor"),
    ColumnDef(name="timestamp", key="timestamp"),
    ColumnDef(name="changes", key="changes", max_width=50),
    ColumnDef(name="schema_version", key="schema_version"),
]


@provenance_app.command("history")
def history(
    entity_type: Annotated[str, typer.Argument(help="Entity type")],
    entity_id: Annotated[str, typer.Argument(help="Entity ID")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 20,
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Show provenance history for an entity."""
    from aperture.cli.main import get_backend

    backend = get_backend()

    try:
        data = backend.get_history(entity_type=entity_type, entity_id=entity_id)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2)

    # Newest first, with limit
    data = data[:limit]

    result = DisplayResult(
        data=data,
        columns=HISTORY_COLUMNS,
        title=f"History: {entity_type}/{entity_id}",
    )
    format_output(result, fmt=format, no_color=no_color)
