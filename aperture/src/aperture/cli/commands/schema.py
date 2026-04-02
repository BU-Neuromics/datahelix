"""Schema inspection commands."""

from __future__ import annotations

from typing import Annotated

import typer

from aperture.cli.display.formatters import format_output
from aperture.models.display import ColumnDef, DisplayResult, OutputFormat

schema_app = typer.Typer(name="schema", help="Schema inspection commands.")


@schema_app.command("list")
def schema_list(
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """List all registered entity types."""
    from aperture.cli.main import get_backend

    backend = get_backend()

    try:
        entity_types = backend.list_entity_types()
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2)

    rows = []
    for et in entity_types:
        try:
            schema = backend.get_entity_type_schema(et)
            fields = schema.get("fields", [])
            rows.append({
                "entity_type": et,
                "field_count": len(fields),
                "searchable": sum(
                    1 for f in fields if isinstance(f, dict) and f.get("search")
                ),
            })
        except Exception:
            rows.append({"entity_type": et, "field_count": "?", "searchable": "?"})

    columns = [
        ColumnDef(name="entity_type", key="entity_type"),
        ColumnDef(name="field_count", key="field_count"),
        ColumnDef(name="searchable", key="searchable"),
    ]
    result = DisplayResult(data=rows, columns=columns, title="Entity Types")
    format_output(result, fmt=format, no_color=no_color)


@schema_app.command("show")
def schema_show(
    entity_type: Annotated[str, typer.Argument(help="Entity type to inspect")],
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Show schema details for an entity type."""
    from aperture.cli.main import get_backend

    backend = get_backend()

    try:
        schema = backend.get_entity_type_schema(entity_type)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    if not schema:
        typer.echo(f"Entity type '{entity_type}' not found.", err=True)
        raise typer.Exit(1)

    if format == OutputFormat.JSON:
        result = DisplayResult(data=schema, is_detail=True)
        format_output(result, fmt=format, no_color=no_color)
        return

    # Table view: show fields
    fields = schema.get("fields", [])
    rows = []
    for f in fields:
        if isinstance(f, dict):
            rows.append({
                "name": f.get("name", ""),
                "type": f.get("type", ""),
                "required": str(f.get("required", False)),
                "indexed": str(f.get("index", False)),
                "searchable": str(bool(f.get("search"))),
            })

    columns = [
        ColumnDef(name="name", key="name"),
        ColumnDef(name="type", key="type"),
        ColumnDef(name="required", key="required"),
        ColumnDef(name="indexed", key="indexed"),
        ColumnDef(name="searchable", key="searchable"),
    ]
    result = DisplayResult(
        data=rows,
        columns=columns,
        title=f"Schema: {entity_type}",
    )
    format_output(result, fmt=format, no_color=no_color)
