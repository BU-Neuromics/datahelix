"""Ingestion command."""

from __future__ import annotations

import csv as csv_mod
import getpass
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from aperture.cli.display.formatters import format_output
from aperture.models.display import ColumnDef, DisplayResult, OutputFormat

ingest_app = typer.Typer()


def _load_records(file_path: Path) -> list[dict]:
    """Load records from CSV or JSON file."""
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        with open(file_path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    elif suffix == ".csv":
        with open(file_path, newline="") as f:
            reader = csv_mod.DictReader(f)
            return list(reader)
    else:
        raise typer.BadParameter(f"Unsupported file format: {suffix}. Use .json or .csv")


@ingest_app.command("ingest")
def ingest(
    entity_type: Annotated[str, typer.Argument(help="Target entity type")],
    file: Annotated[Path, typer.Argument(help="Input file path (.csv or .json)")],
    actor: Annotated[str, typer.Option("--actor", help="Actor identity")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate without ingesting")] = False,
    on_conflict: Annotated[
        str, typer.Option("--on-conflict", help="Conflict strategy: skip|update|error")
    ] = "error",
    format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.TABLE,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
) -> None:
    """Ingest entities from a file."""
    from aperture.cli.main import get_backend

    actor = actor or getpass.getuser()

    if not file.is_file():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(1)

    try:
        records = _load_records(file)
    except Exception as exc:
        typer.echo(f"Error loading file: {exc}", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo(f"Dry run: would ingest {len(records)} records into {entity_type}.")
        return

    backend = get_backend()
    succeeded = 0
    failed = 0
    errors: list[dict] = []

    for i, record in enumerate(records):
        try:
            backend.create_entity(entity_type=entity_type, data=record, actor=actor)
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append({"row": i + 1, "error": str(exc)})

    # Write errors to file
    if errors:
        error_path = file.with_name(f"{file.stem}_errors.csv")
        with open(error_path, "w", newline="") as ef:
            writer = csv_mod.DictWriter(ef, fieldnames=["row", "error"])
            writer.writeheader()
            writer.writerows(errors)
        typer.echo(f"Errors written to {error_path}", err=True)

    summary = {
        "total": len(records),
        "succeeded": succeeded,
        "failed": failed,
        "entity_type": entity_type,
    }
    result = DisplayResult(data=summary, is_detail=True, title="Ingestion Summary")
    format_output(result, fmt=format, no_color=no_color)

    if failed > 0 and succeeded > 0:
        raise typer.Exit(1)  # Partial
    elif failed > 0:
        raise typer.Exit(2)  # All failed
