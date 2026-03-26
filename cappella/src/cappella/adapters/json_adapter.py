import json
from datetime import datetime
from typing import Any, Iterator

import httpx
from jsonpath_ng import parse as jsonpath_parse

from cappella.adapters.base import ExternalSourceAdapter
from cappella.exceptions import AdapterFetchError, AdapterTransformError
from cappella.types import RawRecord, TransformedRecord


class JSONAdapter(ExternalSourceAdapter):
    """Adapter for JSON data sources."""

    supports_incremental: bool = False

    def __init__(self, config: dict[str, Any]):
        self.source: str = config.get("source", "http")
        self.url: str | None = config.get("url")
        self.records_path: str = config.get("records_path", "$[*]")
        self.entity_type: str = config.get("entity_type", "unknown")
        self.external_id_field: str = config.get("external_id_field", "id")
        self.field_map: dict[str, str] = config.get("field_map", {})
        self.vocabulary_map: dict[str, dict[str, str]] = config.get("vocabulary_map", {})
        self.trust_level: int = config.get("trust_level", 50)
        self.name: str = config.get("name", "json")
        self.entity_types: list[str] = [self.entity_type]
        self._upload_data: bytes | None = None

    def fetch(self, since: datetime | None = None, data: bytes | None = None) -> Iterator[RawRecord]:
        if data is not None:
            self._upload_data = data

        try:
            if self.source == "http":
                if not self.url:
                    raise AdapterFetchError("JSONAdapter: url required for http source")
                response = httpx.get(self.url)
                response.raise_for_status()
                raw_text = response.text
            elif self.source == "file":
                if not self.url:
                    raise AdapterFetchError("JSONAdapter: url must be a file path for file source")
                with open(self.url, "r", encoding="utf-8") as f:
                    raw_text = f.read()
            elif self.source == "manual_upload":
                if self._upload_data is None:
                    raise AdapterFetchError("JSONAdapter: no upload data available")
                raw_text = self._upload_data.decode("utf-8")
            else:
                raise AdapterFetchError(f"JSONAdapter: unknown source type: {self.source}")
        except AdapterFetchError:
            raise
        except Exception as e:
            raise AdapterFetchError(f"JSONAdapter fetch failed: {e}", {"error": str(e)})

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise AdapterFetchError(f"JSONAdapter: malformed JSON: {e}", {"error": str(e)})

        try:
            expr = jsonpath_parse(self.records_path)
            matches = expr.find(parsed)
        except Exception as e:
            raise AdapterFetchError(f"JSONAdapter: invalid records_path '{self.records_path}': {e}")

        fetched_at = datetime.utcnow()
        for match in matches:
            record_data = match.value
            if not isinstance(record_data, dict):
                record_data = {"value": record_data}
            external_id = str(record_data.get(self.external_id_field, ""))
            yield RawRecord(
                source_system=self.name,
                external_id=external_id,
                data=record_data,
                fetched_at=fetched_at,
            )

    def transform(self, record: RawRecord) -> TransformedRecord:
        data = dict(record.data)

        if self.external_id_field not in data or not data[self.external_id_field]:
            raise AdapterTransformError(
                f"JSONAdapter: missing external_id_field '{self.external_id_field}'",
                {"record": data},
            )

        transformed: dict[str, Any] = {}
        for key, value in data.items():
            new_key = self.field_map.get(key, key)
            transformed[new_key] = value

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
