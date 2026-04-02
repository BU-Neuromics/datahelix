"""Entity CRUD commands: list, get, create, update, set-availability."""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from aperture.cli.display.formatters import auto_columns, format_output
from aperture.models.display import DisplayResult, OutputFormat

entity_app = typer.Typer()


def _parse_filters(filter_strs: list[str]) -> dict:
    """Parse key=value filter strings into a dict."""
    filters = {}
    for f in filter_strs:
        if "=" not in f:
            raise typer.BadParameter(f"Filter must be key=value, got: {f}")
        key, value = f.split("=", 1)
        filters[key] = value
    return filters


def _load_data(data: str | None, file: Path | None) -> dict:
    """Load entity data from --data JSON string or --file path."""
    if file:
        with open(file) as f:
            return json.load(f)
    if data:
        return json.loads(data)
    # Interactive mode would go here in future
    raise typer.BadParameter("Provide --data or --file")


@entity_app.command("list")
def list_entities(
    entity_type: Annotated[str, typer.Argument(help="Entity type to list")],
    filter: Annotated[
        Optional[list[str]], typer.Option("--filter", "-F", help="Filter as key=value (repeatable)")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 50,
    offset: Annotated[int, typer.Option(help="Offset for pagination")] = 0,
    include_unavailable: Annotated[
        bool, typer.Option("--include-unavailable", help="Include unavailable entities")
    ] = False,
    columns: Annotated[Optional[str], typer.Option(help="Comma-separated column names")] = None,
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """List entities of a given type."""
    from aperture.cli.main import get_backend

    backend = get_backend()
    filters = _parse_filters(filter or [])

    try:
        data = backend.list_entities(
            entity_type=entity_type,
            filters=filters if filters else None,
            limit=min(limit, 500),
            offset=offset,
            include_unavailable=include_unavailable,
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2)

    col_defs = auto_columns(data, entity_type) if not columns else None
    result = DisplayResult(data=data, columns=col_defs or [], title=f"{entity_type} entities")
    format_output(result, fmt=format, no_color=no_color)


@entity_app.command("get")
def get_entity(
    entity_type: Annotated[str, typer.Argument(help="Entity type")],
    entity_id: Annotated[str, typer.Argument(help="Entity ID")],
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Get a single entity by ID."""
    from aperture.cli.main import get_backend

    backend = get_backend()

    try:
        data = backend.get_entity(entity_type=entity_type, entity_id=entity_id)
    except Exception as exc:
        typer.echo(f"Error: {entity_type} '{entity_id}' not found.", err=True)
        raise typer.Exit(1)

    result = DisplayResult(data=data, is_detail=True, title=f"{entity_type}/{entity_id}")
    format_output(result, fmt=format, no_color=no_color)


@entity_app.command("create")
def create_entity(
    entity_type: Annotated[str, typer.Argument(help="Entity type")],
    data: Annotated[Optional[str], typer.Option("--data", help="JSON data string")] = None,
    file: Annotated[Optional[Path], typer.Option("--file", help="JSON file path")] = None,
    actor: Annotated[
        str, typer.Option("--actor", help="Actor identity")
    ] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate without creating")] = False,
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Create a new entity."""
    from aperture.cli.main import get_backend

    actor = actor or getpass.getuser()

    try:
        entity_data = _load_data(data, file)
    except (json.JSONDecodeError, FileNotFoundError, typer.BadParameter) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo("Dry run — entity would be created with:", err=True)
        typer.echo(json.dumps(entity_data, indent=2))
        return

    backend = get_backend()
    try:
        result_data = backend.create_entity(
            entity_type=entity_type, data=entity_data, actor=actor,
        )
    except Exception as exc:
        typer.echo(f"Error creating entity: {exc}", err=True)
        raise typer.Exit(1)

    result = DisplayResult(data=result_data, is_detail=True, title=f"Created {entity_type}")
    format_output(result, fmt=format, no_color=no_color)


@entity_app.command("update")
def update_entity(
    entity_type: Annotated[str, typer.Argument(help="Entity type")],
    entity_id: Annotated[str, typer.Argument(help="Entity ID")],
    data: Annotated[Optional[str], typer.Option("--data", help="JSON patch data")] = None,
    file: Annotated[Optional[Path], typer.Option("--file", help="JSON patch file")] = None,
    actor: Annotated[str, typer.Option("--actor", help="Actor identity")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate without updating")] = False,
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Update an existing entity (partial update)."""
    from aperture.cli.main import get_backend

    actor = actor or getpass.getuser()

    try:
        patch_data = _load_data(data, file)
    except (json.JSONDecodeError, FileNotFoundError, typer.BadParameter) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo("Dry run — entity would be updated with:", err=True)
        typer.echo(json.dumps(patch_data, indent=2))
        return

    backend = get_backend()
    try:
        result_data = backend.update_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            data=patch_data,
            actor=actor,
        )
    except Exception as exc:
        typer.echo(f"Error updating entity: {exc}", err=True)
        raise typer.Exit(1)

    result = DisplayResult(data=result_data, is_detail=True, title=f"Updated {entity_type}/{entity_id}")
    format_output(result, fmt=format, no_color=no_color)


@entity_app.command("set-availability")
def set_availability(
    entity_type: Annotated[str, typer.Argument(help="Entity type")],
    entity_id: Annotated[str, typer.Argument(help="Entity ID")],
    available: Annotated[bool, typer.Argument(help="Availability (true/false)")],
    actor: Annotated[str, typer.Option("--actor", help="Actor identity")] = "",
    reason: Annotated[Optional[str], typer.Option("--reason", help="Reason for change")] = None,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Set entity availability."""
    from aperture.cli.main import get_backend

    actor = actor or getpass.getuser()
    backend = get_backend()

    try:
        result_data = backend.set_availability(
            entity_type=entity_type,
            entity_id=entity_id,
            available=available,
            actor=actor,
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    status_str = "available" if available else "unavailable"
    typer.echo(f"Set {entity_type}/{entity_id} to {status_str}.")
