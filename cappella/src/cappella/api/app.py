import threading
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from cappella.api.jobs import AsyncJobStore
from cappella.exceptions import (
    AdapterError,
    AdapterTransformError,
    CappellaError,
    CanonNoRuleError,
    ConfigError,
    ReconciliationError,
    TriggerError,
)
from cappella.reconciliation.engine import FindingsStore
from cappella.triggers.engine import TriggerEngine


def create_app(config: Any = None) -> FastAPI:
    app = FastAPI(title="Cappella", version="0.1.0")

    # State
    job_store = AsyncJobStore()
    findings_store = FindingsStore()
    app.state.job_store = job_store
    app.state.findings_store = findings_store
    app.state.config = config

    # Initialize trigger engine from config
    raw_trigger_configs = getattr(config, "triggers", []) if config else []
    engine_triggers = []
    for tc in raw_trigger_configs:
        if hasattr(tc, "to_trigger_config"):
            engine_triggers.append(tc.to_trigger_config())
        else:
            engine_triggers.append(tc)
    trigger_engine = TriggerEngine(triggers=engine_triggers if engine_triggers else None)
    app.state.trigger_engine = trigger_engine

    # -------------------------
    # Error handlers
    # -------------------------

    @app.exception_handler(ConfigError)
    async def config_error_handler(request: Request, exc: ConfigError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "ConfigError", "message": str(exc), "context": exc.context},
        )

    @app.exception_handler(AdapterTransformError)
    async def adapter_transform_error_handler(request: Request, exc: AdapterTransformError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "AdapterTransformError", "message": str(exc), "context": exc.context},
        )

    @app.exception_handler(AdapterError)
    async def adapter_error_handler(request: Request, exc: AdapterError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "AdapterError", "message": str(exc), "context": exc.context},
        )

    @app.exception_handler(CanonNoRuleError)
    async def canon_no_rule_error_handler(request: Request, exc: CanonNoRuleError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "CanonNoRuleError", "message": str(exc), "context": exc.context},
        )

    @app.exception_handler(ReconciliationError)
    async def reconciliation_error_handler(request: Request, exc: ReconciliationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "ReconciliationError", "message": str(exc), "context": exc.context},
        )

    @app.exception_handler(TriggerError)
    async def trigger_error_handler(request: Request, exc: TriggerError) -> JSONResponse:
        status_code = 400
        if "invalid signature" in str(exc).lower():
            status_code = 401
        elif "no trigger registered" in str(exc).lower():
            status_code = 404
        return JSONResponse(
            status_code=status_code,
            content={"error": "TriggerError", "message": str(exc), "context": exc.context},
        )

    @app.exception_handler(CappellaError)
    async def cappella_error_handler(request: Request, exc: CappellaError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "CappellaError", "message": str(exc), "context": exc.context},
        )

    # -------------------------
    # Routes
    # -------------------------

    @app.post("/resolve", status_code=202)
    async def start_resolve(body: dict) -> dict:
        run_id = job_store.create_job(job_type="resolve")
        job_store.update_job(run_id, status="running", started_at=datetime.utcnow().isoformat() + "Z")

        def _run() -> None:
            try:
                job_store.update_job(run_id, status="complete", finished_at=datetime.utcnow().isoformat() + "Z")
            except Exception as e:
                job_store.update_job(
                    run_id,
                    status="failed",
                    error=str(e),
                    finished_at=datetime.utcnow().isoformat() + "Z",
                )

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return {"run_id": run_id, "status": "queued"}

    @app.get("/resolve/{run_id}")
    async def get_resolve_status(run_id: str) -> dict:
        job = job_store.get_job(run_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job '{run_id}' not found")
        return job

    @app.post("/ingest/{adapter}", status_code=202)
    async def start_ingest(adapter: str, body: dict = {}) -> dict:
        run_id = job_store.create_job(job_type="ingest", adapter=adapter)
        job_store.update_job(run_id, status="running", started_at=datetime.utcnow().isoformat() + "Z")

        def _run() -> None:
            try:
                job_store.update_job(run_id, status="complete", finished_at=datetime.utcnow().isoformat() + "Z")
            except Exception as e:
                job_store.update_job(
                    run_id,
                    status="failed",
                    error=str(e),
                    finished_at=datetime.utcnow().isoformat() + "Z",
                )

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return {"run_id": run_id, "status": "queued", "adapter": adapter}

    @app.get("/ingest/{run_id}")
    async def get_ingest_status(run_id: str) -> dict:
        job = job_store.get_job(run_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job '{run_id}' not found")
        return job

    @app.post("/triggers/{name}/run", status_code=202)
    async def run_trigger(name: str) -> dict:
        run_id = job_store.create_job(job_type="trigger", trigger=name)
        return {"run_id": run_id, "status": "queued", "trigger": name}

    @app.get("/triggers")
    async def list_triggers() -> dict:
        triggers = getattr(config, "triggers", []) if config else []
        return {
            "triggers": [
                {"name": t.name, "type": t.type}
                for t in triggers
            ]
        }

    @app.post("/webhooks/{path:path}")
    async def handle_webhook(path: str, request: Request) -> dict:
        """Accept incoming webhook POST and dispatch to the matching trigger."""
        payload = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        webhook_path = f"/webhooks/{path}"
        result = trigger_engine.handle_webhook(webhook_path, payload, signature)
        return result

    @app.post("/reconcile")
    async def start_reconcile(body: dict) -> dict:
        entity_type = body.get("entity_type", "unknown")
        return {"findings": [], "entity_type": entity_type}

    @app.get("/findings")
    async def get_findings(
        entity_type: str | None = None,
        check: str | None = None,
        severity: str | None = None,
    ) -> dict:
        results = findings_store.query(
            entity_type=entity_type,
            check=check,
            severity=severity,
        )
        return {
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "check": f.check,
                    "entity_type": f.entity_type,
                    "entity_id": f.entity_id,
                    "severity": f.severity,
                    "detail": f.detail,
                    "suggested_action": f.suggested_action,
                }
                for f in results
            ]
        }

    @app.get("/status")
    async def get_status() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    return app
