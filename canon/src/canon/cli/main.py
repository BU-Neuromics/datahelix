"""Canon CLI entry point."""

from __future__ import annotations

import typer

from canon.cli.commands.plan import plan_command
from canon.cli.commands.run import run_command
from canon.cli.commands.status import status_command
from canon.cli.commands import rules as rules_module

app = typer.Typer(help='Canon — declarative bioinformatics orchestration')

app.command('plan')(plan_command)
app.command('run')(run_command)
app.command('status')(status_command)
app.add_typer(rules_module.app, name='rules')


def main() -> None:
    app()


if __name__ == '__main__':
    main()
