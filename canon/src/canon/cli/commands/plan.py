"""canon plan — dry-run resolution showing REUSE/BUILD decisions."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.tree import Tree

from canon.exceptions import CanonError
from canon.resolver.planner import PlanNode

app = typer.Typer(help="Show the resolution plan without executing anything.")
console = Console()


def _parse_params(param_list: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in param_list:
        if "=" not in item:
            typer.echo(f"Error: invalid --param value {item!r} (expected key=value)", err=True)
            raise typer.Exit(1)
        key, _, val = item.partition("=")
        result[key.strip()] = val.strip()
    return result


def _render_node(node: PlanNode, tree: Tree) -> None:
    params_str = ", ".join(f"{k}={v}" for k, v in node.params.items())
    if node.decision == "REUSE":
        label = (
            f"[green]REUSE[/green] [bold]{node.entity_type}[/bold]"
            f"({params_str})"
            + (f"  → [dim]{node.uri}[/dim]" if node.uri else "")
        )
    else:
        rule_str = f" via [yellow]{node.rule_name}[/yellow]" if node.rule_name else ""
        label = f"[red]BUILD[/red] [bold]{node.entity_type}[/bold]({params_str}){rule_str}"

    branch = tree.add(label)
    for child in node.children:
        _render_node(child, branch)


@app.command()
def plan(
    entity_type: Annotated[str, typer.Argument(help="Mosaic entity type to plan")],
    param: Annotated[
        list[str],
        typer.Option("--param", "-p", help="Identity parameter as key=value (repeatable)"),
    ] = [],
    config: Annotated[
        str | None,
        typer.Option("--config", "-c", help="Path to canon.yaml"),
    ] = None,
) -> None:
    """Show the resolution plan (REUSE/BUILD) without executing anything."""
    from canon.config import CanonConfig
    from canon.resolver.entity_ref import EntityRefResolver
    from canon.resolver.hippo_client import MosaicQueryClient
    from canon.resolver.planner import RecursivePlanner
    from canon.rules.loader import RulesLoader
    from canon.rules.registry import RuleRegistry

    try:
        cfg = CanonConfig.load(config)
    except CanonError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)

    params = _parse_params(param)

    try:
        hippo = MosaicQueryClient(cfg)
        import pathlib
        rules_path = cfg.resolve_rules_file(cfg._config_dir or pathlib.Path.cwd())
        loader = RulesLoader(rules_path)
        rules = loader.load()
        registry = RuleRegistry(rules)
        ref_resolver = EntityRefResolver(hippo)
        planner = RecursivePlanner(
            hippo_client=hippo,
            rule_registry=registry,
            entity_ref_resolver=ref_resolver,
        )
        node = planner.plan(entity_type, params)
    except CanonError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)

    tree = Tree(f"Plan for [bold]{entity_type}[/bold]")
    _render_node(node, tree)
    console.print(tree)
