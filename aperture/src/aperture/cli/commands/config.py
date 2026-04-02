"""Configuration commands: get, set, show."""

from __future__ import annotations

import json
from typing import Annotated

import typer
import yaml

config_app = typer.Typer(name="config", help="Configuration management.")


@config_app.command("show")
def config_show() -> None:
    """Show fully resolved configuration with sources."""
    from aperture.cli.main import get_config

    config = get_config()
    typer.echo(yaml.dump(config.raw, default_flow_style=False).rstrip())


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Config key (dot-separated, e.g. hippo.mode)")],
) -> None:
    """Get a single configuration value."""
    from aperture.cli.main import get_config

    config = get_config()
    value = config.get(key)
    if value is None:
        typer.echo(f"Key '{key}' not found.", err=True)
        raise typer.Exit(1)
    if isinstance(value, dict):
        typer.echo(yaml.dump(value, default_flow_style=False).rstrip())
    else:
        typer.echo(str(value))


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Config key (dot-separated)")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a configuration value in user config (~/.bass/aperture.yaml)."""
    from aperture.cli.main import get_config

    config = get_config()
    # Try to parse as YAML value (for booleans, numbers)
    try:
        parsed = yaml.safe_load(value)
    except yaml.YAMLError:
        parsed = value

    config.set(key, parsed)
    typer.echo(f"Set {key} = {parsed}")
