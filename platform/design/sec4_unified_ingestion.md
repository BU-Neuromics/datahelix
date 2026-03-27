# Section 4: Unified Ingestion Framework

**Status:** Draft v0.1  
**Last updated:** 2026-03-27  
**Scope:** Cross-component (Hippo + Cappella)

---

## 4.1 Motivation

Before this change, ingestion logic was split:
- Hippo had `IngestionPipeline` with hardcoded `ingest_csv/json/jsonl` methods
- Hippo had `ReferenceLoader` ABC for reference data plugins
- Cappella had its own `CSVAdapter`, `JSONAdapter`, `SQLAdapter`, `ExternalSourceAdapter` ABC
- Two separate pipeline implementations, two sets of field mapping logic, two error hierarchies

This creates maintenance burden, divergent behavior, and forces plugin authors to learn two different ABCs depending on whether they're writing a reference loader vs. an operational adapter.

## 4.2 The Unified Model

A single `EntityLoader` ABC lives in Hippo core. Everything that loads data into Hippo — reference loaders, Cappella adapters, CLI ingest, custom scripts — subclasses this one ABC.

```
EntityLoader (ABC, Hippo core)
    │
    ├── ConfigurableLoader (Abstract, Hippo core)
    │   │   Config-driven field_map + vocabulary_map
    │   │
    │   ├── CSVLoader (Concrete, Hippo core)
    │   ├── JSONLoader (Concrete, Hippo core)
    │   ├── SQLLoader (Concrete, Hippo core, extras: hippo[loaders-sql])
    │   └── HippoDSLLoader (Concrete, Hippo core)
    │       Loads structured Hippo DSL YAML directly
    │
    ├── ReferenceLoader subclasses (Hippo plugins)
    │   │   hippo-reference-ensembl, hippo-reference-bioconda, etc.
    │   │   May subclass ConfigurableLoader or EntityLoader directly
    │   └── Discovered via hippo.reference_loaders entry points
    │
    └── Cappella adapter subclasses
        │   Complex integrations (STARLIMS API, paginated REST, SFTP)
        │   Subclass EntityLoader from Hippo
        └── Discovered via cappella.adapters entry points
```

## 4.3 EntityLoader ABC

Lives in `hippo.core.loaders.base`:

```python
class EntityLoader(ABC):
    """Base class for all data loading into Hippo."""

    name: str                          # identifier, e.g. "csv", "ensembl", "starlims"
    entity_types: list[str]            # what this loader produces
    supports_incremental: bool = False

    @abstractmethod
    def fetch(self, since: datetime | None = None, **kwargs) -> Iterator[RawRecord]:
        """Pull records from the source."""
        ...

    @abstractmethod
    def transform(self, record: RawRecord) -> TransformedRecord:
        """Map source record to Hippo entity schema."""
        ...

    def validate(self, record: TransformedRecord, client: Any) -> list[str]:
        """Optional cross-record validation. Default: no validation."""
        return []

    def health_check(self) -> dict[str, Any]:
        """Optional connectivity check."""
        return {"status": "unknown"}
```

## 4.4 ConfigurableLoader

Extends `EntityLoader` with config-driven field mapping and vocabulary normalization. This is the base for all generic loaders (CSV, JSON, SQL) and for simple reference loaders that just need column renaming.

```python
class ConfigurableLoader(EntityLoader):
    """EntityLoader with config-driven field and vocabulary mapping."""

    def __init__(self, config: dict[str, Any]):
        self.entity_type: str = config.get("entity_type", "unknown")
        self.external_id_field: str = config.get("external_id_field", "external_id")
        self.field_map: dict[str, str] = config.get("field_map", {})
        self.vocabulary_map: dict[str, dict[str, str]] = config.get("vocabulary_map", {})
        self.trust_level: int = config.get("trust_level", 50)

    def transform(self, record: RawRecord) -> TransformedRecord:
        """Apply field_map renaming + vocabulary_map normalization."""
        # Generic implementation: rename fields, normalize vocab
        ...
```

## 4.5 Built-in Loaders (Hippo Core)

| Loader | Module | Base install | Notes |
|--------|--------|-------------|-------|
| `CSVLoader` | `hippo.core.loaders.csv` | ✅ (stdlib csv) | File, HTTP URL, or stdin/bytes |
| `JSONLoader` | `hippo.core.loaders.json` | ✅ (stdlib json) | JSONPath for nested records requires `hippo[loaders-json]` |
| `SQLLoader` | `hippo.core.loaders.sql` | `hippo[loaders-sql]` | SQLAlchemy + read-only query validation |
| `HippoDSLLoader` | `hippo.core.loaders.dsl` | ✅ (stdlib yaml) | Structured entity YAML, idempotent via external_id |

## 4.6 Dependency Extras (`pyproject.toml`)

```toml
[project.optional-dependencies]
loaders-sql = ["sqlalchemy>=2.0"]
loaders-json = ["jsonpath-ng>=1.6"]
loaders-all = ["sqlalchemy>=2.0", "jsonpath-ng>=1.6"]
```

CSV and HippoDSL have zero additional dependencies. JSON basic parsing needs no extras; JSONPath for nested records is an optional extra.

## 4.7 `hippo ingest` CLI

The CLI becomes the manual entry point for the loader framework. No triggers, no automation — just run a loader once.

```bash
# Ingest from Hippo DSL YAML (structured entities)
hippo ingest --file entities.yaml

# Ingest from CSV with inline config
hippo ingest --type csv --file donors.csv \
  --entity-type Donor \
  --external-id-field SUBJECT_ID \
  --field-map SUBJECT_ID=external_id SEX=sex DIAGNOSIS=diagnosis

# Ingest from CSV with a config file
hippo ingest --type csv --file donors.csv --config donors_mapping.yaml

# Ingest from SQL (requires hippo[loaders-sql])
hippo ingest --type sql --config lims_query.yaml

# Dry run — show what would be created/updated without writing
hippo ingest --file entities.yaml --dry-run
```

The config file for CSV/JSON/SQL contains the adapter-specific options:

```yaml
# donors_mapping.yaml
entity_type: Donor
external_id_field: SUBJECT_ID
field_map:
  SUBJECT_ID: external_id
  SEX: sex
  AGE_AT_DEATH: age_at_death
  DIAGNOSIS: diagnosis
vocabulary_map:
  diagnosis:
    "CTE": "chronic traumatic encephalopathy"
    "AD": "Alzheimer disease"
```

## 4.8 Idempotency

All loaders use the same upsert-by-ExternalID logic:

1. For each record, look up by `external_id` in Hippo
2. If found and data identical → skip (unchanged)
3. If found and data differs → update
4. If not found → create + register external_id

This is the logic we just fixed in `_upsert_records` (catching `EntityNotFoundError` explicitly).

The `IngestPipeline` class (renamed from `IngestionPipeline`) orchestrates this loop for any `EntityLoader`. It moves from `hippo.core.ingestion` to `hippo.core.loaders.pipeline`.

## 4.9 What Changes in Hippo

| Action | File/Module | Notes |
|--------|-------------|-------|
| **New** | `hippo/src/hippo/core/loaders/__init__.py` | Package exports |
| **New** | `hippo/src/hippo/core/loaders/base.py` | `EntityLoader`, `ConfigurableLoader`, `RawRecord`, `TransformedRecord` |
| **New** | `hippo/src/hippo/core/loaders/csv.py` | `CSVLoader` |
| **New** | `hippo/src/hippo/core/loaders/json.py` | `JSONLoader` |
| **New** | `hippo/src/hippo/core/loaders/sql.py` | `SQLLoader` |
| **New** | `hippo/src/hippo/core/loaders/dsl.py` | `HippoDSLLoader` |
| **New** | `hippo/src/hippo/core/loaders/pipeline.py` | `IngestPipeline` (refactored from `IngestionPipeline`) |
| **New** | `hippo/cli/commands/ingest.py` | `ingest_dsl_file()`, rewired CLI |
| **Modify** | `hippo/src/hippo/core/ingestion.py` | Keep `extract_fts_content`, `flatten_dict`; deprecate `IngestionPipeline` |
| **Modify** | `hippo/pyproject.toml` | Add `loaders-sql`, `loaders-json` extras |
| **Remove** | `hippo/src/hippo/core/data_sources.py` | Replaced by loader config files |

## 4.10 What Changes in Cappella

| Action | Notes |
|--------|-------|
| **Modify** `cappella/src/cappella/adapters/base.py` | `ExternalSourceAdapter` subclasses `hippo.core.loaders.base.EntityLoader` instead of its own ABC |
| **Modify** `cappella/src/cappella/adapters/csv_adapter.py` | Subclass `CSVLoader` from Hippo, add Cappella-specific features (HTTP transport, `manual_upload` source) |
| **Modify** `cappella/src/cappella/adapters/json_adapter.py` | Subclass `JSONLoader` from Hippo |
| **Modify** `cappella/src/cappella/adapters/sql_adapter.py` | Subclass `SQLLoader` from Hippo |
| **Remove** duplicate field_map/vocabulary_map logic | Inherited from `ConfigurableLoader` |

## 4.11 What Does NOT Change

- `ReferenceLoader` ABC and existing reference loader plugins continue to work. They can optionally be migrated to subclass `EntityLoader`, but this is not required in v0.1.
- Canon is not affected — it doesn't load data through this framework.
- The 3-tier test suite continues to work; new contract tests are added.

## 4.12 Test Strategy

**New contract test:** `tests/contracts/test_entity_loader_contract.py`
- Tests `EntityLoader` ABC behavioral contract
- Tests `CSVLoader`, `JSONLoader` against the contract
- Tests idempotency guarantees (create → unchanged → update cycle)

**New platform test:** `tests/platform/test_unified_ingest.py`
- Tests Cappella adapter using Hippo's `CSVLoader` against real Hippo
- Tests that field_map and vocabulary_map from Hippo core work when called from Cappella

**Updated Hippo unit tests:**
- `hippo/tests/core/test_loaders.py` replaces `test_ingestion.py` (same tests, new module paths)
- `hippo/tests/cli/test_ingest.py` (already written, tests DSL ingest + idempotency)

## 4.13 Phased Implementation

**Phase 1 (Hippo):** Create `loaders/` package, implement `EntityLoader` → `ConfigurableLoader` → `CSVLoader/JSONLoader/SQLLoader/HippoDSLLoader` + `IngestPipeline`. Rewrite `hippo ingest` CLI. All Hippo tests green.

**Phase 2 (Cross-component contracts):** Write contract tests at monorepo root. RED until Cappella adopts.

**Phase 3 (Cappella):** Refactor adapters to subclass from Hippo. Remove duplicate logic. All platform tests green.

**Phase 4 (Cleanup):** Deprecate `hippo.core.ingestion.IngestionPipeline`. Update docs.
