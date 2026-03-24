"""canon get — resolve an artifact to its URI."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from canon.exceptions import CanonError

app = typer.Typer(help="Resolve an artifact URI, building it if necessary.")


def _parse_params(param_list: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in param_list:
        if "=" not in item:
            typer.echo(f"Error: invalid --param value {item!r} (expected key=value)", err=True)
            raise typer.Exit(1)
        key, _, val = item.partition("=")
        result[key.strip()] = val.strip()
    return result


@app.command()
def get(
    entity_type: Annotated[str, typer.Argument(help="Hippo entity type to resolve")],
    param: Annotated[
        list[str],
        typer.Option("--param", "-p", help="Identity parameter as key=value (repeatable)"),
    ] = [],
    config: Annotated[
        str | None,
        typer.Option("--config", "-c", help="Path to canon.yaml"),
    ] = None,
) -> None:
    """Resolve an artifact to its URI, building via CWL if needed."""
    from canon.config import CanonConfig
    from canon.executors.cwltool import CwltoolAdapter
    from canon.resolver.entity_ref import EntityRefResolver
    from canon.resolver.hippo_client import HippoQueryClient
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
        hippo = HippoQueryClient(cfg)
        loader = RulesLoader(cfg.resolve_rules_file(cfg._config_dir or __import__("pathlib").Path.cwd()))
        rules = loader.load()
        registry = RuleRegistry(rules)
        ref_resolver = EntityRefResolver(hippo)
        executor = CwltoolAdapter(cfg)
        planner = RecursivePlanner(
            hippo_client=hippo,
            rule_registry=registry,
            entity_ref_resolver=ref_resolver,
            executor=executor,
            work_dir_base=str(cfg.resolve_work_dir(cfg._config_dir or __import__("pathlib").Path.cwd())),
        )
        uri = planner.resolve(entity_type, params)
        typer.echo(uri)
    except CanonError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)
