from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Iterator

from cappella.types import RawRecord, TransformedRecord


class ExternalSourceAdapter(ABC):
    name: str
    entity_types: list[str]
    trust_level: int = 50
    supports_incremental: bool = False

    @abstractmethod
    def fetch(self, since: datetime | None = None) -> Iterator[RawRecord]:
        ...

    @abstractmethod
    def transform(self, record: RawRecord) -> TransformedRecord:
        ...

    def validate(self, record: TransformedRecord, hippo_client: Any) -> list[str]:
        return []

    def health_check(self) -> dict[str, Any]:
        return {"status": "unknown", "detail": "health_check not implemented"}
