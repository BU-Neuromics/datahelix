"""canon rules — list and validate production rules."""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from canon.config import CanonConfig
from canon.exceptions import CanonValidationError
from canon.rule_loader import RulesLoader
from canon.rule_registry import RulesEngine

app = typer.Typer(help='Manage production rules')
console = Console()


def _load(config_path: str, rules_path: Optional[str]):
    config = CanonConfig.from_yaml(config_path)
    if rules_path:
        config = config.model_copy(update={'rules_file': rules_path})
    return config, RulesLoader.from_file(config.rules_file)


@app.command('list')
def list_rules(
    config_path: str = typer.Option('canon.yaml', '--config', help='Path to canon.yaml'),
    rules_path: Optional[str] = typer.Option(None, '--rules', help='Override rules file path'),
) -> None:
    """List all production rules."""
    try:
        _, loader = _load(config_path, rules_path)
    except CanonValidationError as exc:
        console.print(f'[red]{exc}[/red]')
        sys.exit(1)

    table = Table(title='Production Rules')
    table.add_column('rule_name', style='cyan')
    table.add_column('produces_type', style='green')
    table.add_column('requires_types')

    for rule in loader.rules:
        requires = ', '.join(b.entity_type for b in rule.requires) or '—'
        table.add_row(rule.name, rule.produces.entity_type, requires)

    console.print(table)


@app.command('validate')
def validate_rules(
    config_path: str = typer.Option('canon.yaml', '--config', help='Path to canon.yaml'),
    rules_path: Optional[str] = typer.Option(None, '--rules', help='Override rules file path'),
) -> None:
    """Validate production rules for errors and duplicates."""
    try:
        _, loader = _load(config_path, rules_path)
        engine = RulesEngine(loader.rules)
        engine.validate()
    except CanonValidationError as exc:
        console.print(f'[red]Validation failed: {exc}[/red]')
        sys.exit(1)

    console.print('[green]OK — all rules are valid.[/green]')
