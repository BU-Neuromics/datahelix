from typing import Any

from pydantic import BaseModel


class ActionConfig(BaseModel):
    type: str  # "ingest" | "resolve" | "reconcile" | "notify"
    adapter: str | None = None
    entity_type: str | None = None
    parameters: dict[str, Any] = {}


class TriggerConfig(BaseModel):
    name: str
    type: str  # "schedule" | "manual" | "internal_event"
    action: ActionConfig
    schedule: str | None = None  # cron expression for schedule triggers
    event: str | None = None  # event name for internal_event triggers
    on_success: str | None = None  # name of trigger to fire on success
