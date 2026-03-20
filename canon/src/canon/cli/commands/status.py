"""canon status — show recent Canon run history."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

_DB_PATH = Path.home() / '.canon' / 'runs.db'


def status_command(
    limit: int = typer.Option(20, '--limit', help='Number of recent runs to show'),
    config_path: str = typer.Option('canon.yaml', '--config', help='Path to canon.yaml'),
) -> None:
    """Show recent Canon run history."""
    if not _DB_PATH.exists():
        console.print('No runs found.')
        return

    conn = sqlite3.connect(str(_DB_PATH))
    rows = conn.execute(
        """
        SELECT run_id, rule_name, status, started_at, input_count, output_count
        FROM runs
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    if not rows:
        console.print('No runs found.')
        return

    table = Table(title='Canon Run History')
    table.add_column('run_id', style='dim', no_wrap=True)
    table.add_column('rule', style='cyan')
    table.add_column('status')
    table.add_column('started')
    table.add_column('inputs', justify='right')
    table.add_column('outputs', justify='right')

    for run_id, rule_name, status, started_at, input_count, output_count in rows:
        status_style = 'green' if status == 'SUCCEEDED' else 'red'
        table.add_row(
            run_id,
            rule_name,
            f'[{status_style}]{status}[/{status_style}]',
            started_at or '',
            str(input_count),
            str(output_count),
        )

    console.print(table)
