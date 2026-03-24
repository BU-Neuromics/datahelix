"""Canon CLI — semantic artifact resolver for the BASS platform."""

from __future__ import annotations

import sys

import typer

from canon.cli.commands.get import app as get_app
from canon.cli.commands.plan import app as plan_app
from canon.cli.commands.rules import app as rules_app
from canon.cli.commands.status import app as status_app

app = typer.Typer(
    name="canon",
    help="Canon — resolve and build computational artifacts via Hippo + CWL.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(get_app, name="get")
app.add_typer(plan_app, name="plan")
app.add_typer(rules_app, name="rules")
app.add_typer(status_app, name="status")


if __name__ == "__main__":
    app()
