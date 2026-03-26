# Section 3: Adapter System

**Status:** Draft v0.1 (revised)
**Last updated:** 2026-03-25

---

## 3.1 Overview

External adapters are the mechanism by which Cappella ingests structured attribute data from external systems. Each adapter handles one external data format and is responsible for:

1. **Fetching** records from an external source
2. **Parsing** records from the source format (CSV, JSON, XML, etc.)
3. **Transforming** fields to canonical Hippo schema via config-driven field and vocabulary mapping
4. **Declaring** which entity types it produces

**Key design principle:** Format and transport are handled by the adapter. If the data format changes (CSV → JSON), a different adapter type and config are used — not a format flag on a shared adapter. Each adapter type has a purpose-built config schema.

Adapters are Python packages, discovered at startup via the `cappella.adapters` entry point group, and configured in `cappella.yaml`.

---

## 3.2 ExternalSourceAdapter ABC

Defined in Hippo (`hippo.core.adapters`) so the contract is versioned with Hippo. Concrete implementations live in separate adapter packages — not in Cappella core.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator

@dataclass
class RawRecord:
    source_system: str
    external_id: str
    data: dict[str, Any]
    fetched_at: datetime

@dataclass
class TransformedRecord:
    entity_type: str
    data: dict[str, Any]
    external_id: str
    source_system: str
    trust_level: int = 50


class ExternalSourceAdapter(ABC):
    name: str              # entry point name, e.g. "csv", "json", "starlims_api"
    entity_types: list[str]
    trust_level: int = 50
    supports_incremental: bool = False

    @abstractmethod
    def fetch(self, since: datetime | None = None) -> Iterator[RawRecord]: ...

    @abstractmethod
    def transform(self, record: RawRecord) -> TransformedRecord: ...

    def validate(self, record: TransformedRecord, hippo_client: Any) -> list[str]:
        return []

    def health_check(self) -> dict[str, Any]:
        return {"status": "unknown", "detail": "health_check not implemented"}
```

---

## 3.3 Built-in Generic Adapters

Cappella core ships three generic adapters that handle common data formats with config-driven field and vocabulary mapping. These cover the majority of real-world use cases without requiring custom code.

### CSVAdapter

For tabular data delivered as CSV files — uploaded manually, fetched via HTTP GET, or pulled from a local path.

```yaml
adapters:
  starlims_samples:
    type: csv
    trust_level: 80
    config:
      source: http              # "http" | "file" | "manual_upload"
      url: "https://starlims.yourinstitution.edu/export/samples.csv"
      auth_header: "Authorization: Bearer ${STARLIMS_TOKEN}"
      schedule: "0 2 * * *"    # cron; omit for manual_upload
      entity_type: Sample
      external_id_field: SUBJECT_ID
      field_map:
        SUBJECT_ID: external_id
        SEX: sex
        AGE_AT_DEATH: age_at_death
        TISSUE_REGION: tissue
        DIAGNOSIS_CODE: diagnosis
      vocabulary_map:
        diagnosis:
          "CTE": "chronic traumatic encephalopathy"
          "AD": "Alzheimer disease"
          "PD": "Parkinson disease"
```

CSVAdapter reads the declared `field_map` to rename columns, applies `vocabulary_map` to normalize values, and constructs `TransformedRecord` objects ready for upsert. Extra columns not in `field_map` are ignored. Missing required fields raise `AdapterTransformError`.

### JSONAdapter

For systems that expose a JSON API or deliver JSON files.

```yaml
adapters:
  halo_scores:
    type: json
    trust_level: 70
    config:
      source: http
      url: "https://halo.yourinstitution.edu/api/v2/scores"
      auth_header: "X-API-Key: ${HALO_KEY}"
      records_path: "$.data.scores[*]"   # JSONPath to the array of records
      schedule: "0 3 * * *"
      entity_type: HistopathologyScore
      external_id_field: score_id
      field_map:
        score_id: external_id
        sample_barcode: sample_external_id
        algorithm: algorithm_version
        value: score_value
```

`records_path` is a JSONPath expression that locates the array of records within the response. This handles the common case where the actual records are nested inside a response envelope.

### XMLAdapter

For legacy systems and HL7/FHIR-style XML exports.

```yaml
adapters:
  redcap_clinical:
    type: xml
    trust_level: 60
    config:
      source: manual_upload    # uploaded via POST /ingest/redcap_clinical
      records_xpath: "//record"
      entity_type: ClinicalAssessment
      external_id_field: "@record_id"    # XPath attribute reference
      field_map:
        "@record_id": external_id
        "diagnosis/value": diagnosis
        "age_at_enrollment": age_at_enrollment
      vocabulary_map:
        diagnosis:
          "Probable CTE": "chronic traumatic encephalopathy"
```

---

## 3.4 Manual Upload (`manual_upload` source)

Any adapter that declares `source: manual_upload` accepts data via `POST /ingest/{adapter_name}`. This is the primary path for spreadsheet-based onboarding of legacy datasets and for systems where push (not pull) is more natural.

```bash
# Upload a CSV directly
curl -X POST http://cappella:8002/ingest/starlims_samples \
  -H "Content-Type: text/csv" \
  --data-binary @samples_export.csv

# Upload JSON
curl -X POST http://cappella:8002/ingest/halo_scores \
  -H "Content-Type: application/json" \
  -d @halo_export.json
```

The CLI equivalent:

```bash
cappella ingest starlims_samples --file samples_export.csv
cappella ingest halo_scores --file halo_export.json
```

---

## 3.5 Custom Adapter Plugins

When the generic adapters are insufficient — complex authentication flows, paginated APIs, SFTP sources, relational database queries, proprietary protocols — labs write custom adapter packages.

A custom adapter implements `ExternalSourceAdapter` directly, handling both transport and transformation in code. Field and vocabulary maps may be externalized to the adapter's own config section if the author chooses, but this is the adapter author's decision, not enforced by Cappella core.

```python
# cappella_adapter_starlims/adapter.py
class STARLIMSAdapter(ExternalSourceAdapter):
    name = "starlims_api"
    entity_types = ["Donor", "Sample"]
    supports_incremental = True

    def __init__(self, config: dict) -> None:
        self._client = STARLIMSClient(
            base_url=config["base_url"],
            token=config["auth_token"],
        )

    def fetch(self, since=None) -> Iterator[RawRecord]:
        for page in self._client.get_samples(modified_since=since):
            for record in page["records"]:
                yield RawRecord(
                    source_system="starlims",
                    external_id=record["SUBJECT_ID"],
                    data=record,
                    fetched_at=datetime.utcnow(),
                )

    def transform(self, record: RawRecord) -> TransformedRecord:
        # All mapping logic lives here in code
        ...
```

Registered via entry point:
```toml
[project.entry-points."cappella.adapters"]
starlims_api = "cappella_adapter_starlims:STARLIMSAdapter"
```

---

## 3.6 Adapter Error Handling

| Error type | Handling |
|-----------|----------|
| Fetch failure (network, auth) | Abort run, log `adapter_run_failed` event, do not retry automatically |
| `AdapterTransformError` | Skip this record, log error, continue with remaining records |
| `validate()` returns errors | Block upsert for this record, record `HarmonizationConflict` event, continue |
| HippoClient write error | Abort run, log error with record context |

Partial success is always preferred. A run that transforms 95/100 records is reported as `partial_success`, not failure.

---

## 3.7 Adapter Run Audit

Each run produces a structured `adapter_run_completed` log event:

```json
{
  "event": "adapter_run_completed",
  "run_id": "uuid-run-123",
  "adapter": "starlims_samples",
  "mode": "incremental",
  "fetched": 150,
  "transformed": 149,
  "upserted": 23,
  "skipped_identical": 126,
  "failed_transform": 1,
  "conflicts_detected": 2,
  "status": "partial_success",
  "duration_seconds": 46.2
}
```

In v0.2 this becomes an `AdapterRun` Hippo entity for long-term queryability.
