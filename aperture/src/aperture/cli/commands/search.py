"""Search command."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from aperture.cli.display.formatters import auto_columns, format_output
from aperture.models.display import DisplayResult, OutputFormat

search_app = typer.Typer()


@search_app.command("search")
def search(
    entity_type: Annotated[str, typer.Argument(help="Entity type to search")],
    query: Annotated[str, typer.Argument(help="Search query")],
    field: Annotated[Optional[str], typer.Option("--field", help="Restrict to specific field")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 10,
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Search entities by query string."""
    from aperture.cli.main import get_backend

    backend = get_backend()

    try:
        data = backend.search(
            entity_type=entity_type,
            query=query,
            field=field,
            limit=min(limit, 100),
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2)

    col_defs = auto_columns(data, entity_type)
    result = DisplayResult(data=data, columns=col_defs, title=f"Search: {query}")
    format_output(result, fmt=format, no_color=no_color)
