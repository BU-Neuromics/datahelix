from typing import Optional

import typer

app = typer.Typer(
    name="cappella",
    help="Cappella - Harmonization engine for the DataHelix platform",
    no_args_is_help=True,
)

trigger_app = typer.Typer(name="trigger", help="Trigger management commands")
app.add_typer(trigger_app)


def _load_config_or_default(config_path: Optional[str] = None):
    from cappella.config import CappellaConfig, load_config

    if config_path:
        try:
            return load_config(config_path)
        except Exception as e:
            typer.echo(f"Failed to load config: {e}", err=True)
            raise typer.Exit(1)
    return CappellaConfig()


class _NullHippoClient:
    """No-op Hippo client for in-process dry-run when no server is configured."""

    def schema_references(self, entity_type: str) -> list:
        return []

    def query(self, entity_type: str, filters: dict) -> list:
        return []

    def get_by_external_id(self, system: str, external_id: str):
        return None

    def create(self, entity_type: str, data: dict, context: dict) -> dict:
        return data

    def update(self, entity_id: str, data: dict, context: dict) -> dict:
        return data


@app.command("resolve")
def resolve_cmd(
    entity_type: str = typer.Argument(..., help="Entity type to resolve"),
    criteria: Optional[str] = typer.Option(None, "--criteria", "-c", help="JSON criteria"),
    strategy: str = typer.Option("most_recent", "--strategy", "-s", help="Selection strategy"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Resolve a harmonized collection for an entity type."""
    import json

    from cappella.resolver.collection import CollectionResolver, ResolutionRequest

    _load_config_or_default(config_path)

    criteria_dict: dict = {}
    if criteria:
        try:
            criteria_dict = json.loads(criteria)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid JSON in --criteria: {e}", err=True)
            raise typer.Exit(1)

    request = ResolutionRequest(
        entity_type=entity_type,
        criteria=criteria_dict,
        selection={"strategy": strategy},
    )

    resolver = CollectionResolver()
    collection = resolver.resolve(request, _NullHippoClient())

    typer.echo(f"entity_type: {collection.request['entity_type']}")
    typer.echo(f"resolved: {len(collection.resolved)}")
    typer.echo(f"unresolved: {len(collection.unresolved)}")


@app.command("ingest")
def ingest_cmd(
    adapter: str = typer.Argument(..., help="Adapter name to run"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Config file path"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO datetime for incremental fetch"),
) -> None:
    """Run an ingest adapter."""
    from datetime import datetime

    from cappella.adapters.registry import AdapterRegistry
    from cappella.exceptions import ConfigError
    from cappella.ingest.pipeline import IngestPipeline

    cfg = _load_config_or_default(config_path)

    try:
        registry = AdapterRegistry.from_config(cfg)
    except ConfigError as e:
        typer.echo(f"Config error: {e}", err=True)
        raise typer.Exit(1)

    try:
        adapter_obj = registry.get(adapter)
    except ConfigError as e:
        typer.echo(f"Adapter '{adapter}' not found: {e}", err=True)
        raise typer.Exit(1)

    since_dt: Optional[datetime] = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError as e:
            typer.echo(f"Invalid --since datetime: {e}", err=True)
            raise typer.Exit(1)

    pipeline = IngestPipeline(hippo_client=None)
    result = pipeline.run(adapter_obj, since=since_dt)

    typer.echo(f"adapter: {result.adapter_name}")
    typer.echo(f"status: {result.status}")
    typer.echo(f"fetched: {result.fetched}")
    typer.echo(f"transformed: {result.transformed}")
    typer.echo(f"upserted: {result.upserted}")
    if result.errors:
        for err in result.errors:
            typer.echo(f"  error: {err}", err=True)


@app.command("reconcile")
def reconcile_cmd(
    entity_type: str = typer.Argument(..., help="Entity type to reconcile"),
    checks: Optional[str] = typer.Option(None, "--checks", help="Comma-separated check names"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Run reconciliation checks for an entity type."""
    from cappella.reconciliation.engine import ReconciliationEngine, ReconciliationRequest

    _load_config_or_default(config_path)

    check_list: Optional[list] = None
    if checks:
        check_list = [c.strip() for c in checks.split(",") if c.strip()]

    request = ReconciliationRequest(entity_type=entity_type, checks=check_list)
    engine = ReconciliationEngine()
    findings = engine.run(request, _NullHippoClient())

    typer.echo(f"entity_type: {entity_type}")
    typer.echo(f"findings: {len(findings)}")
    for f in findings:
        typer.echo(f"  [{f.severity.upper()}] {f.check} | {f.entity_id} — {f.detail}")


@app.command("status")
def status_cmd(
    url: str = typer.Option("http://localhost:8000", "--url", "-u", help="Cappella server URL"),
) -> None:
    """Check the health status of the Cappella server."""
    try:
        import httpx

        response = httpx.get(f"{url}/status", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            typer.echo(f"Status: {data.get('status', 'unknown')}")
            typer.echo(f"Version: {data.get('version', 'unknown')}")
        else:
            typer.echo(f"Server returned HTTP {response.status_code}", err=True)
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Cannot connect to {url}: {e}", err=True)
        raise typer.Exit(1)


@app.command("findings")
def findings_cmd(
    url: str = typer.Option("http://localhost:8000", "--url", "-u", help="Cappella server URL"),
    entity_type: Optional[str] = typer.Option(None, "--entity-type", "-e", help="Filter by entity type"),
    check: Optional[str] = typer.Option(None, "--check", help="Filter by check name"),
    severity: Optional[str] = typer.Option(None, "--severity", help="Filter by severity"),
) -> None:
    """Query reconciliation findings."""
    try:
        import httpx

        params: dict = {}
        if entity_type:
            params["entity_type"] = entity_type
        if check:
            params["check"] = check
        if severity:
            params["severity"] = severity
        response = httpx.get(f"{url}/findings", params=params, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            findings = data.get("findings", [])
            if not findings:
                typer.echo("No findings.")
            for f in findings:
                typer.echo(f"[{f['severity'].upper()}] {f['check']} | {f['entity_type']}:{f['entity_id']} — {f['detail']}")
        else:
            typer.echo(f"Server returned HTTP {response.status_code}", err=True)
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Cannot connect to {url}: {e}", err=True)
        raise typer.Exit(1)


@trigger_app.command("run")
def trigger_run_cmd(
    name: str = typer.Argument(..., help="Trigger name to execute"),
    url: str = typer.Option("http://localhost:8000", "--url", "-u", help="Cappella server URL"),
) -> None:
    """Manually run a trigger."""
    try:
        import httpx

        response = httpx.post(f"{url}/triggers/{name}/run", timeout=5.0)
        if response.status_code == 202:
            data = response.json()
            typer.echo(f"Trigger '{name}' queued. run_id={data.get('run_id')}")
        else:
            typer.echo(f"Server returned HTTP {response.status_code}", err=True)
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Cannot connect to {url}: {e}", err=True)
        raise typer.Exit(1)


@trigger_app.command("list")
def trigger_list_cmd(
    url: str = typer.Option("http://localhost:8000", "--url", "-u", help="Cappella server URL"),
) -> None:
    """List all configured triggers."""
    try:
        import httpx

        response = httpx.get(f"{url}/triggers", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            triggers = data.get("triggers", [])
            if not triggers:
                typer.echo("No triggers configured.")
            for t in triggers:
                typer.echo(f"{t['name']} ({t['type']})")
        else:
            typer.echo(f"Server returned HTTP {response.status_code}", err=True)
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Cannot connect to {url}: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
