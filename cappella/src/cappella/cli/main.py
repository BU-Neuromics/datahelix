from typing import Optional

import typer

app = typer.Typer(
    name="cappella",
    help="Cappella - Harmonization engine for the BASS platform",
    no_args_is_help=True,
)

trigger_app = typer.Typer(name="trigger", help="Trigger management commands")
app.add_typer(trigger_app)


@app.command("resolve")
def resolve_cmd(
    entity_type: str = typer.Argument(..., help="Entity type to resolve"),
    criteria: Optional[str] = typer.Option(None, "--criteria", "-c", help="JSON criteria"),
    strategy: str = typer.Option("most_recent", "--strategy", "-s", help="Selection strategy"),
    config: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Resolve a harmonized collection for an entity type."""
    typer.echo(f"Resolving collection for entity_type='{entity_type}' strategy='{strategy}'")
    typer.echo("(Not connected to Hippo — use the API server for full resolution)")


@app.command("ingest")
def ingest_cmd(
    adapter: str = typer.Argument(..., help="Adapter name to run"),
    config: Optional[str] = typer.Option(None, "--config", help="Config file path"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO datetime for incremental fetch"),
) -> None:
    """Run an ingest adapter."""
    typer.echo(f"Running ingest adapter='{adapter}'")
    if since:
        typer.echo(f"  Incremental since: {since}")
    typer.echo("(Not connected to Hippo — use the API server for full ingest)")


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
    except Exception as e:
        typer.echo(f"Cannot connect to {url}: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
