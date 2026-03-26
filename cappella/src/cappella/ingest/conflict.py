from dataclasses import dataclass
from typing import Any


@dataclass
class ConflictResolution:
    winning_value: Any
    resolution: str  # "existing_wins" | "incoming_wins" | "manual_review_required"
    event: dict[str, Any]


class ConflictResolver:
    """Resolves conflicts between existing and incoming field values based on trust levels."""

    def resolve(
        self,
        entity_id: str,
        field: str,
        existing_value: Any,
        existing_source: str,
        existing_trust: int,
        incoming_value: Any,
        incoming_source: str,
        incoming_trust: int,
    ) -> tuple[Any, str]:
        """
        Returns (winning_value, resolution_str).

        resolution_str is one of:
          - "existing_wins"
          - "incoming_wins"
          - "manual_review_required"
        """
        if existing_trust > incoming_trust:
            resolution = "existing_wins"
            winning_value = existing_value
        elif incoming_trust > existing_trust:
            resolution = "incoming_wins"
            winning_value = incoming_value
        else:
            resolution = "manual_review_required"
            winning_value = existing_value  # default to existing when equal

        event = self._build_event(
            entity_id=entity_id,
            field=field,
            existing_value=existing_value,
            existing_source=existing_source,
            existing_trust=existing_trust,
            incoming_value=incoming_value,
            incoming_source=incoming_source,
            incoming_trust=incoming_trust,
            resolution=resolution,
            winning_value=winning_value,
        )

        return winning_value, resolution

    def _build_event(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "type": "HarmonizationConflict",
            **kwargs,
        }
