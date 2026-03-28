from datetime import datetime
from typing import Any, Iterator

from hippo.core.loaders.sql import SQLLoader

from cappella.exceptions import AdapterFetchError, AdapterTransformError, ConfigError
from cappella.types import RawRecord, TransformedRecord

_FORBIDDEN_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "EXEC"}


def _check_query_safety(query: str) -> None:
    """Raise ConfigError if query contains write operations."""
    upper = query.upper()
    for keyword in _FORBIDDEN_KEYWORDS:
        # Simple word boundary check
        import re
        if re.search(r"\b" + keyword + r"\b", upper):
            raise ConfigError(
                f"SQLAdapter: query contains forbidden keyword '{keyword}'",
                {"query": query},
            )


class SQLAdapter(SQLLoader):
    """Adapter for SQL database sources.

    Subclasses hippo.core.loaders.SQLLoader so that Cappella SQL adapters
    participate in the unified ingestion framework. __init__ does not call
    super().__init__() because SQLLoader raises ValueError on forbidden queries
    while Cappella's contract requires ConfigError; all attributes are set
    directly. fetch/transform use Cappella's typed RawRecord / TransformedRecord.
    """

    supports_incremental: bool = True

    def __init__(self, config: dict[str, Any]):
        # Do not call super().__init__(): SQLLoader validates queries with ValueError
        # but Cappella's contract requires ConfigError (see _check_query_safety below).
        self.connection_string: str = config.get("connection_string", "")
        self.entity_type: str = config.get("entity_type", "unknown")
        self.external_id_field: str = config.get("external_id_field", "id")
        self.query: str = config.get("query", "")
        self.incremental_query: str | None = config.get("incremental_query")
        self.field_map: dict[str, str] = config.get("field_map", {})
        self.vocabulary_map: dict[str, dict[str, str]] = config.get("vocabulary_map", {})
        self.trust_level: int = config.get("trust_level", 50)
        self.name: str = config.get("name", "sql")
        self.entity_types: list[str] = [self.entity_type]

        # Validate query safety (raises ConfigError, not ValueError)
        if self.query:
            _check_query_safety(self.query)
        if self.incremental_query:
            _check_query_safety(self.incremental_query)

    def fetch(self, since: datetime | None = None, **kwargs: Any) -> Iterator[RawRecord]:
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            raise AdapterFetchError("SQLAdapter requires sqlalchemy: pip install sqlalchemy")

        try:
            engine = create_engine(self.connection_string)
        except Exception as e:
            raise AdapterFetchError(
                f"SQLAdapter: cannot create engine: {e}",
                {"connection_string": self.connection_string, "error": str(e)},
            )

        try:
            with engine.connect() as conn:
                if since is not None and self.incremental_query:
                    stmt = text(self.incremental_query)
                    result = conn.execute(stmt, {"since": since})
                else:
                    stmt = text(self.query)
                    result = conn.execute(stmt)

                fetched_at = datetime.utcnow()
                for row in result:
                    row_dict = dict(row._mapping)
                    external_id = str(row_dict.get(self.external_id_field, ""))
                    yield RawRecord(
                        source_system=self.name,
                        external_id=external_id,
                        data=row_dict,
                        fetched_at=fetched_at,
                    )
        except AdapterFetchError:
            raise
        except Exception as e:
            raise AdapterFetchError(
                f"SQLAdapter fetch failed: {e}",
                {"error": str(e)},
            )

    def transform(self, record: RawRecord) -> TransformedRecord:  # type: ignore[override]
        data = dict(record.data)

        if self.external_id_field not in data:
            raise AdapterTransformError(
                f"SQLAdapter: missing external_id_field '{self.external_id_field}'",
                {"record": data},
            )

        # Only keep mapped fields (if field_map is provided)
        if self.field_map:
            transformed: dict[str, Any] = {}
            for src_key, dst_key in self.field_map.items():
                if src_key in data:
                    transformed[dst_key] = data[src_key]
        else:
            transformed = dict(data)

        for field_name, vocab in self.vocabulary_map.items():
            if field_name in transformed:
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
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self.connection_string)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
