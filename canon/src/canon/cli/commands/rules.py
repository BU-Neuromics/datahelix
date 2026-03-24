"""canon rules — list and validate production rules."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from canon.exceptions import CanonError, CanonRuleValidationError

app = typer.Typer(help="List and validate Canon production rules.")
console = Console()


def _load_cfg_and_rules(config: str | None):
    import pathlib
    from canon.config import CanonConfig
    from canon.rules.loader import RulesLoader

    cfg = CanonConfig.load(config)
    rules_path = cfg.resolve_rules_file(cfg._config_dir or pathlib.Path.cwd())
    loader = RulesLoader(rules_path)
    rules = loader.load()
    return cfg, rules


@app.command("list")
def rules_list(
    config: Annotated[
        str | None,
        typer.Option("--config", "-c", help="Path to canon.yaml"),
    ] = None,
) -> None:
    """List all installed production rules."""
    try:
        _, rules = _load_cfg_and_rules(config)
    except CanonError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not rules:
        console.print("[dim]No rules found.[/dim]")
        return

    table = Table(title="Canon Production Rules", show_lines=False)
    table.add_column("Name", style="bold cyan")
    table.add_column("Produces", style="green")
    table.add_column("Requires", style="yellow")
    table.add_column("Description")

    for rule in rules:
        params_str = ", ".join(
            f"{k}={v}" for k, v in rule.produces.match.items()
        )
        produces_str = f"{rule.produces.entity_type}({params_str})"
        requires_str = ", ".join(r.entity_type for r in rule.requires) or "—"
        table.add_row(rule.name, produces_str, requires_str, rule.description or "")

    console.print(table)


@app.command("validate")
def rules_validate(
    config: Annotated[
        str | None,
        typer.Option("--config", "-c", help="Path to canon.yaml"),
    ] = None,
) -> None:
    """Validate all production rules and report any errors."""
    try:
        _, rules = _load_cfg_and_rules(config)
        console.print(f"[green]✓[/green] {len(rules)} rule(s) validated successfully.")
    except CanonRuleValidationError as e:
        console.print(f"[red]Validation failed:[/red]\n{e}", err=True)
        sys.exit(1)
    except CanonError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)
