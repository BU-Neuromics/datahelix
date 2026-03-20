"""canon plan — show the execution plan for a target entity."""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.tree import Tree

from canon.config import CanonConfig
from canon.exceptions import CanonCycleError, CanonPlanningError
from canon.hippo_client import HippoClient
from canon.plan import CanonTask, EntityRef
from canon.planner import SemanticPlanner
from canon.rule_loader import RulesLoader
from canon.rule_registry import RulesEngine

console = Console()


def plan_command(
    entity_type: str = typer.Option(..., '--entity-type', help='Target entity type'),
    metadata: list[str] = typer.Option([], '--metadata', help='key=value metadata pairs'),
    config_path: str = typer.Option('canon.yaml', '--config', help='Path to canon.yaml'),
    rules_path: Optional[str] = typer.Option(None, '--rules', help='Override rules file path'),
) -> None:
    """Show the execution plan for producing an entity."""
    config = CanonConfig.from_yaml(config_path)
    if rules_path:
        config = config.model_copy(update={'rules_file': rules_path})

    metadata_spec: dict[str, str] = {}
    for item in metadata:
        if '=' not in item:
            console.print(f'[red]Invalid metadata pair (expected key=value): {item!r}[/red]')
            sys.exit(1)
        k, _, v = item.partition('=')
        metadata_spec[k.strip()] = v.strip()

    loader = RulesLoader.from_file(config.rules_file)
    engine = RulesEngine(loader.rules)
    hippo = HippoClient.from_config(config)
    planner = SemanticPlanner(config, hippo, engine)

    try:
        plan = planner.plan(entity_type, metadata_spec)
    except CanonCycleError as exc:
        console.print(f'[red]Cycle detected: {exc}[/red]')
        sys.exit(1)
    except CanonPlanningError as exc:
        console.print(f'[red]Planning error: {exc}[/red]')
        sys.exit(1)

    tree = Tree(f'[bold]Plan for [cyan]{entity_type}[/cyan][/bold]')
    for node in plan.nodes:
        if isinstance(node, EntityRef):
            tree.add(
                f'[green]\\[REUSE] {node.entity_id} ({node.entity_type})[/green]'
            )
        elif isinstance(node, CanonTask):
            tree.add(
                f'[yellow]\\[BUILD] {node.rule_name} ({node.wildcard_bindings.as_dict()})[/yellow]'
            )
    console.print(tree)
