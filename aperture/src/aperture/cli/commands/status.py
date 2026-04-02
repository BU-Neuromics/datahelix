"""System status command."""

from __future__ import annotations

from typing import Annotated

import typer

from aperture.cli.display.formatters import format_output
from aperture.models.display import ColumnDef, DisplayResult, OutputFormat

status_app = typer.Typer()

STATUS_COLUMNS = [
    ColumnDef(name="Component", key="component"),
    ColumnDef(name="Mode", key="mode"),
    ColumnDef(name="URL/Path", key="url"),
    ColumnDef(name="Status", key="status"),
    ColumnDef(name="Version", key="version"),
    ColumnDef(name="Entities", key="entity_types"),
]


@status_app.command("status")
def status(
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Show BASS platform status."""
    from aperture.cli.main import get_backend

    backend = get_backend()

    try:
        status_data = backend.status()
    except Exception as exc:
        typer.echo(f"Error checking status: {exc}", err=True)
        raise typer.Exit(2)

    # Normalize url/path field
    url_or_path = status_data.get("url") or status_data.get("path", "")
    row = {
        "component": status_data.get("component", "hippo"),
        "mode": status_data.get("mode", "unknown"),
        "url": url_or_path,
        "status": status_data.get("status", "unknown"),
        "version": status_data.get("version", "unknown"),
        "entity_types": str(status_data.get("entity_types", 0)),
    }

    result = DisplayResult(data=[row], columns=STATUS_COLUMNS, title="BASS Status")
    format_output(result, fmt=format, no_color=no_color)

    if status_data.get("status") != "healthy":
        raise typer.Exit(1)
