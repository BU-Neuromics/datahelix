from datetime import datetime
from typing import Any, Iterator

from mosaic.core.loaders import EntityLoader

from cappella.types import RawRecord, TransformedRecord


class ExternalSourceAdapter(EntityLoader):
    """Base class for all Cappella external source adapters.

    Subclasses mosaic.core.loaders.EntityLoader so that Cappella adapters
    participate in the unified ingestion framework. The fetch/transform
    abstract methods use Cappella's richer typed RawRecord / TransformedRecord
    instead of plain dicts, which is fine at runtime because Python does not
    enforce generic type annotations.
    """

    name: str
    entity_types: list[str]
    trust_level: int = 50
    supports_incremental: bool = False

    def validate(self, record: TransformedRecord, hippo_client: Any = None) -> list[str]:  # type: ignore[override]
        return []

    def health_check(self) -> dict[str, Any]:
        return {"status": "unknown", "detail": "health_check not implemented"}
