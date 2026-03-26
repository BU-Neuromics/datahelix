import json
import sys
from datetime import datetime
from typing import Any

_log_format = "json"
_log_output = "stdout"


def configure(format: str = "json", output: str = "stdout") -> None:
    global _log_format, _log_output
    _log_format = format
    _log_output = output


def emit_event(event_type: str, **kwargs: Any) -> None:
    """Emit a structured log event."""
    payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **kwargs,
    }

    if _log_format == "json":
        line = json.dumps(payload)
    else:
        parts = [f"event={event_type}"]
        for k, v in kwargs.items():
            parts.append(f"{k}={v}")
        line = " ".join(parts)

    print(line, file=sys.stdout)


def log_run_started(run_id: str, adapter_name: str, **kwargs: Any) -> None:
    emit_event("adapter_run_started", run_id=run_id, adapter=adapter_name, **kwargs)


def log_run_completed(run_id: str, adapter_name: str, status: str, **kwargs: Any) -> None:
    emit_event("adapter_run_completed", run_id=run_id, adapter=adapter_name, status=status, **kwargs)


def log_conflict(
    run_id: str,
    entity_id: str,
    field: str,
    resolution: str,
    **kwargs: Any,
) -> None:
    emit_event(
        "harmonization_conflict",
        run_id=run_id,
        entity_id=entity_id,
        field=field,
        resolution=resolution,
        **kwargs,
    )
