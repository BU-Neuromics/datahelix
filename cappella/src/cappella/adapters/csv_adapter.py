import csv
import io
from datetime import datetime
from typing import Any, Iterator

import httpx

from cappella.adapters.base import ExternalSourceAdapter
from cappella.exceptions import AdapterFetchError, AdapterTransformError
from cappella.types import RawRecord, TransformedRecord


class CSVAdapter(ExternalSourceAdapter):
    """Adapter for CSV data sources (file, HTTP URL, or manual upload)."""

    supports_incremental: bool = False

    def __init__(self, config: dict[str, Any]):
        self.source: str = config.get("source", "file")
        self.url: str | None = config.get("url")
        self.entity_type: str = config.get("entity_type", "unknown")
        self.external_id_field: str = config.get("external_id_field", "id")
        self.field_map: dict[str, str] = config.get("field_map", {})
        self.vocabulary_map: dict[str, dict[str, str]] = config.get("vocabulary_map", {})
        self.trust_level: int = config.get("trust_level", 50)
        self.name: str = config.get("name", "csv")
        self.entity_types: list[str] = [self.entity_type]
        self._upload_data: bytes | None = None

    def fetch(self, since: datetime | None = None, data: bytes | None = None) -> Iterator[RawRecord]:
        if data is not None:
            self._upload_data = data

        try:
            if self.source == "http":
                if not self.url:
                    raise AdapterFetchError("CSVAdapter: url required for http source")
                response = httpx.get(self.url)
                response.raise_for_status()
                content = response.text
            elif self.source == "file":
                if not self.url:
                    raise AdapterFetchError("CSVAdapter: url must be a file path for file source")
                with open(self.url, "r", newline="", encoding="utf-8") as f:
                    content = f.read()
            elif self.source == "manual_upload":
                if self._upload_data is None:
                    raise AdapterFetchError("CSVAdapter: no upload data available")
                content = self._upload_data.decode("utf-8")
            else:
                raise AdapterFetchError(f"CSVAdapter: unknown source type: {self.source}")
        except AdapterFetchError:
            raise
        except Exception as e:
            raise AdapterFetchError(f"CSVAdapter fetch failed: {e}", {"error": str(e)})

        reader = csv.DictReader(io.StringIO(content))
        fetched_at = datetime.utcnow()
        for row in reader:
            row_dict = dict(row)
            external_id = row_dict.get(self.external_id_field, "")
            yield RawRecord(
                source_system=self.name,
                external_id=str(external_id),
                data=row_dict,
                fetched_at=fetched_at,
            )

    def transform(self, record: RawRecord) -> TransformedRecord:
        data = dict(record.data)

        if self.external_id_field not in data or not data[self.external_id_field]:
            raise AdapterTransformError(
                f"CSVAdapter: missing external_id_field '{self.external_id_field}'",
                {"record": data},
            )

        # Apply field_map renaming
        transformed: dict[str, Any] = {}
        for key, value in data.items():
            new_key = self.field_map.get(key, key)
            transformed[new_key] = value

        # Apply vocabulary_map normalization
        for field_name, vocab in self.vocabulary_map.items():
            if field_name in transformed:
                transformed[field_name] = vocab.get(transformed[field_name], transformed[field_name])

        external_id = data.get(self.external_id_field, record.external_id)

        return TransformedRecord(
            entity_type=self.entity_type,
            data=transformed,
            external_id=str(external_id),
            source_system=record.source_system,
            trust_level=self.trust_level,
        )

    def health_check(self) -> dict[str, Any]:
        if self.source == "http" and self.url:
            try:
                response = httpx.head(self.url, timeout=5.0)
                return {"status": "ok", "http_status": response.status_code}
            except Exception as e:
                return {"status": "error", "detail": str(e)}
        return {"status": "ok", "detail": "file or manual_upload source"}
