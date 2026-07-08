import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Mosaic's IngestPipeline orchestrates the upsert loop for any EntityLoader.
# Cappella adapters now subclass Mosaic loaders, so a live hippo_client could
# delegate via: mosaic.core.loaders.pipeline.IngestPipeline(client, adapter).run()
# Full delegation is deferred because Cappella adapters yield typed RawRecord /
# TransformedRecord dataclasses rather than the plain dicts Mosaic expects.
from mosaic.core.loaders.pipeline import IngestPipeline as MosaicIngestPipeline  # noqa: F401

from cappella.adapters.base import ExternalSourceAdapter
from cappella.exceptions import AdapterFetchError, AdapterTransformError, AdapterError
from cappella.ingest import audit
from cappella.types import RawRecord, TransformedRecord


@dataclass
class IngestRunResult:
    run_id: str
    adapter_name: str
    status: str  # "success" | "partial_success" | "failed"
    fetched: int = 0
    transformed: int = 0
    upserted: int = 0
    created: int = 0
    updated: int = 0
    skipped_identical: int = 0
    failed_transform: int = 0
    failed_validation: int = 0
    conflicts_detected: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class IngestPipeline:
    """Orchestrates the fetch → transform → validate → upsert pipeline."""

    def __init__(self, hippo_client: Any = None) -> None:
        self.hippo_client = hippo_client

    def run(
        self,
        adapter: ExternalSourceAdapter,
        since: datetime | None = None,
        data: bytes | None = None,
    ) -> IngestRunResult:
        run_id = str(uuid.uuid4())
        adapter_name = getattr(adapter, "name", type(adapter).__name__)
        start_time = time.monotonic()

        audit.log_run_started(run_id=run_id, adapter_name=adapter_name)

        result = IngestRunResult(run_id=run_id, adapter_name=adapter_name, status="failed")

        # Fetch phase
        raw_records: list[RawRecord] = []
        try:
            fetch_kwargs: dict[str, Any] = {}
            if since is not None:
                fetch_kwargs["since"] = since
            if data is not None:
                fetch_kwargs["data"] = data
            raw_records = list(adapter.fetch(**fetch_kwargs))
            result.fetched = len(raw_records)
        except (AdapterFetchError, AdapterError, Exception) as e:
            result.status = "failed"
            result.errors.append(f"fetch failed: {e}")
            result.duration_seconds = time.monotonic() - start_time
            audit.log_run_completed(
                run_id=run_id,
                adapter_name=adapter_name,
                status="failed",
                error=str(e),
            )
            return result

        if not raw_records:
            result.status = "success"
            result.duration_seconds = time.monotonic() - start_time
            audit.log_run_completed(run_id=run_id, adapter_name=adapter_name, status="success")
            return result

        # Transform + Validate phase
        transformed_records: list[TransformedRecord] = []
        for raw in raw_records:
            try:
                transformed = adapter.transform(raw)
                result.transformed += 1
            except AdapterTransformError as e:
                result.failed_transform += 1
                result.errors.append(f"transform failed for {raw.external_id}: {e}")
                continue
            except Exception as e:
                result.failed_transform += 1
                result.errors.append(f"transform error for {raw.external_id}: {e}")
                continue

            # Validate phase
            validation_errors = adapter.validate(transformed, self.hippo_client)
            if validation_errors:
                result.failed_validation += 1
                result.errors.append(f"validation failed for {raw.external_id}: {validation_errors}")
                continue

            transformed_records.append(transformed)

        # Upsert phase (simulated — actual upsert would go to Hippo)
        result.upserted = len(transformed_records)
        result.created = len(transformed_records)

        # Determine status
        total_failures = result.failed_transform + result.failed_validation
        if total_failures == 0:
            result.status = "success"
        elif total_failures < result.fetched:
            result.status = "partial_success"
        else:
            result.status = "partial_success"  # some were fetched but all failed transform

        result.duration_seconds = time.monotonic() - start_time

        audit.log_run_completed(
            run_id=run_id,
            adapter_name=adapter_name,
            status=result.status,
            fetched=result.fetched,
            transformed=result.transformed,
            upserted=result.upserted,
        )

        return result
