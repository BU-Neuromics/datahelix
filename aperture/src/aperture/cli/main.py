"""BASS CLI entry point - main Typer application."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from aperture import __version__
from aperture.cli.commands.config import config_app
from aperture.cli.commands.entity import entity_app
from aperture.cli.commands.ingest import ingest_app
from aperture.cli.commands.provenance import provenance_app
from aperture.cli.commands.schema import schema_app
from aperture.cli.commands.search import search_app
from aperture.cli.commands.status import status_app

# Module-level state for lazy initialization
_config: "ApertureConfig | None" = None
_backend: "HippoBackend | None" = None
_config_path: Path | None = None
_hippo_url_override: str | None = None

app = typer.Typer(
    name="bass",
    help="BASS CLI - Bioinformatics Analysis Software System interface.",
    no_args_is_help=True,
    add_completion=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"bass {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    config: Annotated[
        Optional[Path],
        typer.Option("--config", help="Path to config file"),
    ] = None,
    hippo_url: Annotated[
        Optional[str],
        typer.Option("--hippo-url", help="Override Hippo URL (sets REST mode)"),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-data output"),
    ] = False,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    """BASS CLI - interface to the BASS platform."""
    global _config_path, _hippo_url_override
    _config_path = config
    _hippo_url_override = hippo_url


def get_config() -> "ApertureConfig":
    """Get or create the resolved configuration."""
    global _config
    if _config is None:
        from aperture.config.settings import ApertureConfig

        _config = ApertureConfig(config_path=_config_path)
        # Apply --hippo-url override
        if _hippo_url_override:
            _config._raw.setdefault("hippo", {})["mode"] = "rest"
            _config._raw["hippo"]["url"] = _hippo_url_override
    return _config


def get_backend() -> "HippoBackend":
    """Get or create the backend adapter."""
    global _backend
    if _backend is None:
        from aperture.backends.factory import create_backend

        _backend = create_backend(get_config())
    return _backend


# Register entity commands directly on the top-level app
app.command("list")(entity_app.registered_commands[0].callback)
app.command("get")(entity_app.registered_commands[1].callback)
app.command("create")(entity_app.registered_commands[2].callback)
app.command("update")(entity_app.registered_commands[3].callback)
app.command("set-availability")(entity_app.registered_commands[4].callback)

# Register search directly on top-level
app.command("search")(search_app.registered_commands[0].callback)

# Register history directly on top-level
app.command("history")(provenance_app.registered_commands[0].callback)

# Register ingest directly on top-level
app.command("ingest")(ingest_app.registered_commands[0].callback)

# Register status directly on top-level
app.command("status")(status_app.registered_commands[0].callback)

# Register sub-apps
app.add_typer(schema_app, name="schema", help="Schema inspection commands.")
app.add_typer(config_app, name="config", help="Configuration management.")


if __name__ == "__main__":
    app()
