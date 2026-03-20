"""canon run — execute a production plan end-to-end."""

from __future__ import annotations

import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from canon.config import CanonConfig
from canon.exceptions import CanonCycleError, CanonPlanningError
from canon.executors.base import RunStatus
from canon.executors.container import ContainerExecutor
from canon.executors.local import LocalProcessExecutor
from canon.hippo_client import HippoClient
from canon.ingestion import OutputIngestionPipeline, ProvenanceRecorder
from canon.plan import CanonTask, EntityRef
from canon.planner import SemanticPlanner
from canon.rule_loader import RulesLoader
from canon.rule_registry import RulesEngine

console = Console()

_DB_PATH = Path.home() / '.canon' / 'runs.db'


def _ensure_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT,
            rule_name TEXT,
            status TEXT,
            started_at TEXT,
            finished_at TEXT,
            input_count INTEGER,
            output_count INTEGER
        )
        """
    )
    conn.commit()
    return conn


def _record_run(
    conn: sqlite3.Connection,
    run_id: str,
    rule_name: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    input_count: int,
    output_count: int,
) -> None:
    conn.execute(
        "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            rule_name,
            status,
            started_at.isoformat(),
            finished_at.isoformat(),
            input_count,
            output_count,
        ),
    )
    conn.commit()


def run_command(
    entity_type: str = typer.Option(..., '--entity-type', help='Target entity type'),
    metadata: list[str] = typer.Option([], '--metadata', help='key=value metadata pairs'),
    config_path: str = typer.Option('canon.yaml', '--config', help='Path to canon.yaml'),
    rules_path: Optional[str] = typer.Option(None, '--rules', help='Override rules file path'),
) -> None:
    """Execute a production plan, ingesting outputs into Hippo."""
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

    if config.executor == 'container':
        executor = ContainerExecutor(config, rules_engine=engine)
    else:
        executor = LocalProcessExecutor(config, rules_engine=engine)

    ingestion = OutputIngestionPipeline(hippo)
    provenance = ProvenanceRecorder(hippo)
    db = _ensure_db(_DB_PATH)

    try:
        plan = planner.plan(entity_type, metadata_spec)
    except CanonCycleError as exc:
        console.print(f'[red]Cycle detected: {exc}[/red]')
        sys.exit(1)
    except CanonPlanningError as exc:
        console.print(f'[red]Planning error: {exc}[/red]')
        sys.exit(1)

    for node in plan.nodes:
        if isinstance(node, EntityRef):
            console.print(f'Reusing entity {node.entity_id}')
            continue

        if not isinstance(node, CanonTask):
            continue

        task: CanonTask = node
        input_entity_ids = [
            e.get('id', '') for e in task.input_entities.values()
        ]

        console.print(f'[bold]Running rule:[/bold] {task.rule_name}')
        started_at = datetime.now(tz=timezone.utc)

        executor_inputs = executor.render(task)
        handle = executor.submit(executor_inputs)

        while True:
            status = executor.poll(handle)
            if status == RunStatus.RUNNING:
                time.sleep(2)
                continue
            break

        finished_at = datetime.now(tz=timezone.utc)

        if status == RunStatus.FAILED:
            console.print(f'[red]Run failed for rule {task.rule_name!r} (run_id={handle.run_id})[/red]')
            _record_run(
                db, handle.run_id, task.rule_name, 'FAILED',
                started_at, finished_at, len(input_entity_ids), 0,
            )
            sys.exit(1)

        work_dir = executor._runs[handle.run_id]['work_dir']
        output_ids = ingestion.ingest(work_dir)

        for oid in output_ids:
            console.print(f'Ingested: {oid}')

        provenance.record(
            task=task,
            input_entity_ids=input_entity_ids,
            output_entity_ids=output_ids,
            executor_type=handle.executor_type,
            work_dir=work_dir,
            started_at=started_at,
            finished_at=finished_at,
            status='SUCCEEDED',
        )

        _record_run(
            db, handle.run_id, task.rule_name, 'SUCCEEDED',
            started_at, finished_at, len(input_entity_ids), len(output_ids),
        )
