from datetime import datetime
from typing import Any, Iterator

from cappella.adapters.base import ExternalSourceAdapter
from cappella.exceptions import AdapterFetchError, AdapterTransformError
from cappella.types import RawRecord, TransformedRecord


class XMLAdapter(ExternalSourceAdapter):
    """Adapter for XML data sources."""

    supports_incremental: bool = False

    def __init__(self, config: dict[str, Any]):
        self.source: str = config.get("source", "manual_upload")
        self.url: str | None = config.get("url")
        self.records_xpath: str = config.get("records_xpath", "//record")
        self.entity_type: str = config.get("entity_type", "unknown")
        self.external_id_field: str = config.get("external_id_field", "id")
        self.field_map: dict[str, str] = config.get("field_map", {})
        self.vocabulary_map: dict[str, dict[str, str]] = config.get("vocabulary_map", {})
        self.trust_level: int = config.get("trust_level", 50)
        self.name: str = config.get("name", "xml")
        self.entity_types: list[str] = [self.entity_type]
        self._upload_data: bytes | None = None

    def fetch(self, since: datetime | None = None, data: bytes | None = None) -> Iterator[RawRecord]:
        try:
            from lxml import etree
        except ImportError:
            raise AdapterFetchError("XMLAdapter requires lxml: pip install lxml")

        if data is not None:
            self._upload_data = data

        try:
            if self.source == "file":
                if not self.url:
                    raise AdapterFetchError("XMLAdapter: url must be a file path for file source")
                with open(self.url, "rb") as f:
                    raw_bytes = f.read()
            elif self.source == "manual_upload":
                if self._upload_data is None:
                    raise AdapterFetchError("XMLAdapter: no upload data available")
                raw_bytes = self._upload_data
            else:
                raise AdapterFetchError(f"XMLAdapter: unknown source type: {self.source}")
        except AdapterFetchError:
            raise
        except Exception as e:
            raise AdapterFetchError(f"XMLAdapter fetch failed: {e}", {"error": str(e)})

        try:
            root = etree.fromstring(raw_bytes)
        except etree.XMLSyntaxError as e:
            raise AdapterFetchError(f"XMLAdapter: malformed XML: {e}", {"error": str(e)})

        elements = root.xpath(self.records_xpath)
        fetched_at = datetime.utcnow()

        for element in elements:
            record_data: dict[str, Any] = {}

            # Extract all field_map keys using XPath/attribute expressions
            for field_key, target_field in self.field_map.items():
                value = self._extract_field(element, field_key)
                record_data[field_key] = value

            # Also extract external_id_field if not already in field_map
            if self.external_id_field not in record_data:
                value = self._extract_field(element, self.external_id_field)
                if value is not None:
                    record_data[self.external_id_field] = value

            external_id = str(record_data.get(self.external_id_field, ""))
            yield RawRecord(
                source_system=self.name,
                external_id=external_id,
                data=record_data,
                fetched_at=fetched_at,
            )

    def _extract_field(self, element: Any, field_key: str) -> Any:
        """Extract a value from an XML element using XPath or @attr syntax."""
        try:
            if field_key.startswith("@"):
                attr_name = field_key[1:]
                return element.get(attr_name)
            else:
                results = element.xpath(field_key)
                if results:
                    result = results[0]
                    if hasattr(result, "text"):
                        return result.text
                    return str(result)
                return None
        except Exception:
            return None

    def transform(self, record: RawRecord) -> TransformedRecord:
        data = dict(record.data)

        if self.external_id_field not in data or data[self.external_id_field] is None:
            raise AdapterTransformError(
                f"XMLAdapter: missing external_id_field '{self.external_id_field}'",
                {"record": data},
            )

        transformed: dict[str, Any] = {}
        for key, value in data.items():
            new_key = self.field_map.get(key, key)
            transformed[new_key] = value

        for field_name, vocab in self.vocabulary_map.items():
            if field_name in transformed and transformed[field_name] is not None:
                transformed[field_name] = vocab.get(str(transformed[field_name]), transformed[field_name])

        external_id = data.get(self.external_id_field, record.external_id)

        return TransformedRecord(
            entity_type=self.entity_type,
            data=transformed,
            external_id=str(external_id),
            source_system=record.source_system,
            trust_level=self.trust_level,
        )

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "detail": "xml adapter"}
