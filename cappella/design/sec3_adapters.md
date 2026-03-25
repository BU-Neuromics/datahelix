# Section 3: Adapter System

**Status:** Draft v0.1  
**Last updated:** 2026-03-25

---

## 3.1 Overview

External adapters are the mechanism by which Cappella ingests structured attribute data from systems outside the BASS platform. Each adapter handles one external system and is responsible for:

1. **Fetching** records from the external system (pull model, v0.1)
2. **Transforming** records to canonical Hippo schema
3. **Declaring** which entity types it produces
4. **Optionally validating** cross-record consistency before upsert

Adapters are Python packages, discovered at startup via the `cappella.adapters` entry point group, and configured in `cappella.yaml`.

---

## 3.2 ExternalSourceAdapter ABC

Defined in Hippo (`hippo.core.adapters`) so the contract is versioned with Hippo, not Cappella. Concrete implementations live in Cappella or separate community packages.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator

@dataclass
class RawRecord:
    """Unprocessed record as received from the external system."""
    source_system: str
    external_id: str          # stable identifier in the source system
    entity_hint: str | None   # suggested entity type, if source provides it
    data: dict[str, Any]
    fetched_at: datetime

@dataclass
class TransformedRecord:
    """Record ready for upsert into Hippo."""
    entity_type: str
    data: dict[str, Any]      # field names must match Hippo schema
    external_id: str
    source_system: str
    trust_level: int = 50     # 0-100; higher trust wins conflicts


class ExternalSourceAdapter(ABC):
    """Abstract base class for Cappella external source adapters."""

    #: Entry point name, e.g. "starlims", "halo", "redcap"
    name: str

    #: Entity types this adapter can produce, e.g. ["Donor", "Sample"]
    entity_types: list[str]

    #: Trust level for conflict resolution (0-100). Higher wins.
    #: Default 50. Set higher for authoritative sources (e.g., sequencing core = 80).
    trust_level: int = 50

    #: Whether this adapter can pull only changed records since a timestamp.
    supports_incremental: bool = False

    @abstractmethod
    def fetch(self, since: datetime | None = None) -> Iterator[RawRecord]:
        """Pull records from the external system.

        Args:
            since: If provided and supports_incremental=True, only return records
                   changed since this timestamp. If None, perform a full sync.

        Yields:
            RawRecord instances, one per external record.
        """
        ...

    @abstractmethod
    def transform(self, record: RawRecord) -> TransformedRecord:
        """Map external record to canonical Hippo schema.

        This is where field renaming, vocabulary normalization, type coercion,
        and any source-specific logic lives. Must be deterministic and side-effect-free.

        Args:
            record: A raw record from fetch().

        Returns:
            TransformedRecord ready for upsert.

        Raises:
            AdapterTransformError: If the record cannot be meaningfully transformed.
                The ingest pipeline will log this and continue with the next record.
        """
        ...

    def validate(
        self,
        record: TransformedRecord,
        hippo_client: Any,  # HippoClient
    ) -> list[str]:
        """Optional cross-record validation against existing Hippo state.

        Called after transform(), before upsert. Returning a non-empty list
        blocks the upsert for this record and records the errors as a
        HarmonizationConflict event.

        Default implementation: no validation (returns []).
        """
        return []

    def health_check(self) -> dict[str, Any]:
        """Optional connectivity check for the external system.

        Returns a dict with at minimum {"status": "ok" | "error", "detail": str}.
        Used by GET /status to report adapter health.
        """
        return {"status": "unknown", "detail": "health_check not implemented"}
```

---

## 3.3 Adapter Configuration (`cappella.yaml`)

Each adapter is configured in `cappella.yaml` under `adapters:`. The config is passed to the adapter's `__init__` at startup.

```yaml
adapters:
  starlims:
    enabled: true
    trust_level: 80          # authoritative source for sample/donor identity
    config:
      base_url: "https://starlims.yourinstitution.edu/api/v2"
      auth_token: "${STARLIMS_API_TOKEN}"
      entity_types: [Donor, Sample]
      field_map:
        # External field name → Hippo field name
        SUBJECT_ID: external_id
        SEX: sex
        AGE_AT_DEATH: age_at_death
        DIAGNOSIS: diagnosis
        TISSUE_CODE: tissue

  halo:
    enabled: true
    trust_level: 70
    config:
      base_url: "https://halo.yourinstitution.edu/export"
      api_key: "${HALO_API_KEY}"
      entity_types: [HistopathologyScore]
      field_map:
        SAMPLE_BARCODE: sample_external_id
        ALGORITHM: algorithm_version
        SCORE: score_value

  manual:
    enabled: true
    trust_level: 60
    config:
      # Manual ingest adapter — accepts CSV/JSON payloads via POST /ingest/manual
      entity_types: [Donor, Sample, SequencingDataset]
```

### Field Mapping

**Opinion (mark for review):** Field mapping is declared in `cappella.yaml` (adapter config), not in the adapter code. This allows labs to reconfigure mappings without releasing a new adapter package. The `field_map` config is passed to the adapter's `transform()` as a utility dict; the adapter applies it. Complex transformations (vocabulary normalization, type coercion) that can't be expressed as field renames live in adapter code.

---

## 3.4 Vocabulary Normalization

Different source systems often use different controlled vocabularies for the same concept. A `Diagnosis` field might be `"Alzheimer's Disease"` in STARLIMS, `"AD"` in REDCap, and `"Alzheimer disease"` in HALO.

Cappella provides a `VocabularyNormalizer` utility:

```python
class VocabularyNormalizer:
    def normalize(self, source_system: str, field: str, value: str) -> str:
        """Return canonical Hippo value for a source-specific vocabulary term."""
        ...
```

Vocabulary mappings are declared in the adapter config:

```yaml
adapters:
  starlims:
    config:
      vocabulary:
        diagnosis:
          "Alzheimer's Disease": "Alzheimer disease"
          "ALS": "amyotrophic lateral sclerosis"
          "CTE": "chronic traumatic encephalopathy"
```

The `VocabularyNormalizer` applies these mappings in `transform()`. Unmapped values pass through as-is and are flagged in the `TransformedRecord.warnings` field (not a hard error).

**Opinion (mark for review):** Vocabulary maps live in config, not code, to allow non-engineer correction without a release cycle. A future Hippo feature (ontology/vocabulary entity type) could replace static maps with dynamic lookups.

---

## 3.5 Built-in Adapters (v0.1)

### ManualIngestAdapter

Accepts CSV or JSON payloads via `POST /ingest/manual`. Validates field names against the declared entity type schema. No external connectivity required. The foundation for spreadsheet-based onboarding of legacy datasets.

```
POST /ingest/manual
Content-Type: text/csv
X-Entity-Type: Sample

sample_id,donor_id,tissue,diagnosis
S001,D001,DLPFC,CTE
S002,D001,DLPFC,CTE
```

### STARLIMSAdapter (stub)

Stub implementation in Cappella core. Returns empty fetch results with a log warning until a concrete implementation is developed or the `cappella-adapter-starlims` community package is installed.

### HALOAdapter (stub), REDCapAdapter (stub)

Same pattern — stubs that log a warning and return empty results.

**Opinion (mark for review):** Shipping stubs for the three priority external systems ensures the entry points and config schema are tested from day 1, even without real API connectivity. Real implementations can be developed and released as separate packages without touching Cappella core.

---

## 3.6 Adapter Error Handling

| Error type | Handling |
|-----------|----------|
| `AdapterFetchError` | Log error, abort this sync run, record in audit log, do not retry automatically (next scheduled run will retry) |
| `AdapterTransformError` | Log error for this record, continue with remaining records, record failed record count in audit log |
| `HippoClient error` | Log error, abort sync run, record in audit log |
| `validate()` returns errors | Block upsert for this record, record as `HarmonizationConflict` event, continue with remaining records |

**Partial success is always preferred over all-or-nothing.** A sync run that ingests 95 out of 100 records is better than one that aborts at the first error. Failed records are logged with full context for manual review.

---

## 3.7 Adapter Run Audit

Each adapter sync run produces a structured `AdapterRun` log entry:

```json
{
  "run_id": "uuid-run-123",
  "adapter": "starlims",
  "trigger": "nightly_starlims_sync",
  "started_at": "2026-03-25T02:00:01Z",
  "finished_at": "2026-03-25T02:00:47Z",
  "mode": "incremental",
  "since": "2026-03-24T02:00:00Z",
  "fetched": 150,
  "transformed": 149,
  "upserted": 23,
  "skipped_identical": 126,
  "failed_transform": 1,
  "conflicts_detected": 2,
  "status": "partial_success"
}
```

In v0.1, this is written to structured logs. In v0.2, it becomes an `AdapterRun` Hippo entity for long-term audit queryability.
