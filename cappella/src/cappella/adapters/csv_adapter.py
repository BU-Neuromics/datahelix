import csv
import io
from datetime import datetime
from typing import Any, Iterator

import httpx

from hippo.core.loaders.csv import CSVLoader

from cappella.exceptions import AdapterFetchError, AdapterTransformError
from cappella.types import RawRecord, TransformedRecord


class CSVAdapter(CSVLoader):
    """Adapter for CSV data sources (file, HTTP URL, or manual upload).

    Subclasses hippo.core.loaders.CSVLoader so that Cappella CSV adapters
    participate in the unified ingestion framework. field_map, vocabulary_map,
    entity_type, external_id_field, and trust_level are inherited from
    ConfigurableLoader. The fetch/transform overrides use Cappella's richer
    typed RawRecord / TransformedRecord and add manual_upload source support.
    """

    supports_incremental: bool = False

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)  # ConfigurableLoader sets entity_type, external_id_field,
        #   field_map, vocabulary_map, trust_level, entity_types
        self.source: str = config.get("source", "file")
        self.url: str | None = config.get("url")
        self.name: str = config.get("name", "csv")
        self._upload_data: bytes | None = None

    def fetch(self, since: datetime | None = None, data: bytes | None = None, **kwargs: Any) -> Iterator[RawRecord]:
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

    def transform(self, record: RawRecord) -> TransformedRecord:  # type: ignore[override]
        data = dict(record.data)

        if self.external_id_field not in data or not data[self.external_id_field]:
            raise AdapterTransformError(
                f"CSVAdapter: missing external_id_field '{self.external_id_field}'",
                {"record": data},
            )

        # Apply field_map renaming (self.field_map inherited from ConfigurableLoader)
        transformed: dict[str, Any] = {}
        for key, value in data.items():
            new_key = self.field_map.get(key, key)
            transformed[new_key] = value

        # Apply vocabulary_map normalization (self.vocabulary_map inherited from ConfigurableLoader)
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
