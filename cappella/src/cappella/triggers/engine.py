import threading
from datetime import datetime
from typing import Any, Callable

from cappella.exceptions import TriggerError
from cappella.ingest import audit
from cappella.triggers.models import TriggerConfig


class InternalEventBus:
    """Simple synchronous event bus with cycle detection."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}
        self._emitting: set[str] = set()

    def subscribe(self, event: str, handler: Callable) -> None:
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(handler)

    def emit(self, event: str, payload: dict | None = None) -> None:
        if event in self._emitting:
            raise TriggerError(
                f"InternalEventBus: cycle detected for event '{event}'",
                {"event": event},
            )

        self._emitting.add(event)
        try:
            handlers = self._subscribers.get(event, [])
            for handler in handlers:
                handler(event, payload or {})
        finally:
            self._emitting.discard(event)

    def has_subscribers(self, event: str) -> bool:
        return bool(self._subscribers.get(event))


class TriggerExecutor:
    """Executes trigger actions synchronously."""

    def __init__(
        self,
        triggers: dict[str, TriggerConfig],
        event_bus: InternalEventBus | None = None,
    ) -> None:
        self._triggers = triggers
        self._event_bus = event_bus

    def run(self, trigger_name: str) -> dict[str, Any]:
        """Execute a trigger by name. Returns result dict."""
        if trigger_name not in self._triggers:
            raise TriggerError(
                f"TriggerExecutor: unknown trigger '{trigger_name}'",
                {"trigger": trigger_name},
            )

        trigger = self._triggers[trigger_name]
        audit.emit_event("trigger_fired", trigger=trigger_name, action=trigger.action.type)

        try:
            result = self._execute_action(trigger)
            if trigger.on_success and self._event_bus:
                try:
                    self._event_bus.emit(trigger.on_success)
                except TriggerError:
                    pass
            return {"status": "success", "trigger": trigger_name, "result": result}
        except Exception as e:
            audit.emit_event("trigger_failed", trigger=trigger_name, error=str(e))
            raise TriggerError(
                f"TriggerExecutor: trigger '{trigger_name}' failed: {e}",
                {"trigger": trigger_name, "error": str(e)},
            )

    def _execute_action(self, trigger: TriggerConfig) -> dict[str, Any]:
        action = trigger.action
        return {
            "action_type": action.type,
            "adapter": action.adapter,
            "entity_type": action.entity_type,
            "executed_at": datetime.utcnow().isoformat() + "Z",
        }


class TriggerEngine:
    """Manages trigger scheduling and execution."""

    def __init__(self, triggers: list[TriggerConfig] | None = None) -> None:
        self._triggers: dict[str, TriggerConfig] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._event_bus = InternalEventBus()

        if triggers:
            for t in triggers:
                self.add_trigger(t)

        self._executor = TriggerExecutor(self._triggers, self._event_bus)

    def add_trigger(self, trigger: TriggerConfig) -> None:
        self._triggers[trigger.name] = trigger
        if trigger.type == "internal_event" and trigger.event:
            self._event_bus.subscribe(
                trigger.event,
                lambda event, payload, t=trigger: self._executor.run(t.name),
            )

    def schedule_trigger(self, trigger_name: str) -> None:
        """Schedule a trigger to run based on its cron expression."""
        if trigger_name not in self._triggers:
            raise TriggerError(f"Unknown trigger: '{trigger_name}'")

        trigger = self._triggers[trigger_name]
        if trigger.type != "schedule" or not trigger.schedule:
            raise TriggerError(f"Trigger '{trigger_name}' is not a schedule trigger")

        self._schedule_next(trigger_name, trigger.schedule)

    def _schedule_next(self, trigger_name: str, cron_expr: str) -> None:
        try:
            from croniter import croniter
            now = datetime.utcnow()
            cron = croniter(cron_expr, now)
            next_run = cron.get_next(datetime)
            delay = (next_run - now).total_seconds()
            delay = max(0, delay)
        except Exception as e:
            raise TriggerError(f"Invalid cron expression '{cron_expr}': {e}")

        def _run() -> None:
            try:
                self._executor.run(trigger_name)
            except Exception:
                pass
            # Reschedule
            self._schedule_next(trigger_name, cron_expr)

        timer = threading.Timer(delay, _run)
        timer.daemon = True
        self._timers[trigger_name] = timer
        timer.start()

    def cancel_trigger(self, trigger_name: str) -> None:
        if trigger_name in self._timers:
            self._timers[trigger_name].cancel()
            del self._timers[trigger_name]

    def run_manual(self, trigger_name: str) -> dict[str, Any]:
        """Execute a trigger manually."""
        return self._executor.run(trigger_name)

    def emit_event(self, event: str, payload: dict | None = None) -> None:
        """Emit an internal event."""
        self._event_bus.emit(event, payload)

    def get_event_bus(self) -> InternalEventBus:
        return self._event_bus

    def parse_cron(self, cron_expr: str) -> bool:
        """Validate a cron expression. Returns True if valid."""
        try:
            from croniter import croniter
            return croniter.is_valid(cron_expr)
        except Exception:
            return False
