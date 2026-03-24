"""canon status — show recent WorkflowRun entities."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from canon.exceptions import CanonError

app = typer.Typer(help="Show recent Canon workflow runs from Hippo.")
console = Console()

_STATUS_COLORS = {
    "running": "yellow",
    "completed": "green",
    "failed": "red",
}


@app.command()
def status(
    config: Annotated[
        str | None,
        typer.Option("--config", "-c", help="Path to canon.yaml"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of runs to show"),
    ] = 20,
) -> None:
    """Show recent WorkflowRun entities from Hippo."""
    from canon.config import CanonConfig
    from canon.resolver.hippo_client import HippoQueryClient

    try:
        cfg = CanonConfig.load(config)
    except CanonError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        hippo = HippoQueryClient(cfg)
        runs = hippo.find_entities("WorkflowRun", {})
    except CanonError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not runs:
        console.print("[dim]No WorkflowRun records found.[/dim]")
        return

    # Sort by started_at descending if available, then limit
    runs_sorted = sorted(
        runs,
        key=lambda e: e.data.get("started_at", "") or "",
        reverse=True,
    )[:limit]

    table = Table(title=f"Recent WorkflowRuns (last {limit})", show_lines=False)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Rule", style="cyan")
    table.add_column("Target", style="bold")
    table.add_column("Status")
    table.add_column("Started At")
    table.add_column("Completed At")

    for run in runs_sorted:
        d = run.data
        status_val = d.get("status", "unknown")
        color = _STATUS_COLORS.get(status_val, "white")
        table.add_row(
            run.id[:8] + "…" if len(run.id) > 9 else run.id,
            d.get("rule_name", "—"),
            d.get("target_entity_type", "—"),
            f"[{color}]{status_val}[/{color}]",
            (d.get("started_at") or "—")[:19],
            (d.get("completed_at") or "—")[:19],
        )

    console.print(table)
