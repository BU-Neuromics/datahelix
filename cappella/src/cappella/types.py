from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawRecord:
    source_system: str
    external_id: str
    data: dict[str, Any]
    fetched_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TransformedRecord:
    entity_type: str
    data: dict[str, Any]
    external_id: str
    source_system: str
    trust_level: int = 50


@dataclass
class ResolvedItem:
    sample_id: str
    entity: dict[str, Any]
    status: str
    canon_decision: Any = None


@dataclass
class UnresolvedItem:
    sample_id: str
    reason: str
    detail: str = ""


@dataclass
class HarmonizedCollection:
    request: dict[str, Any]
    selection: dict[str, Any]
    resolved: list[ResolvedItem]
    unresolved: list[UnresolvedItem]
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def resolved_count(self) -> int:
        return len(self.resolved)

    @property
    def unresolved_count(self) -> int:
        return len(self.unresolved)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "selection": self.selection,
            "resolved": [
                {
                    "sample_id": r.sample_id,
                    "entity": r.entity,
                    "status": r.status,
                    "canon_decision": (
                        {
                            "decision": r.canon_decision.decision,
                            "uri": r.canon_decision.uri,
                        }
                        if r.canon_decision is not None
                        else None
                    ),
                }
                for r in self.resolved
            ],
            "unresolved": [
                {
                    "sample_id": u.sample_id,
                    "reason": u.reason,
                    "detail": u.detail,
                }
                for u in self.unresolved
            ],
            "provenance": self.provenance,
            "resolved_count": self.resolved_count,
            "unresolved_count": self.unresolved_count,
        }


class SelectionStrategy(ABC):
    @abstractmethod
    def select(self, candidates: list[dict], filters: dict | None = None) -> dict | None:
        ...
