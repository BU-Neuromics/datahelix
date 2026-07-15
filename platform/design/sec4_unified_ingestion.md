# Section 4: Unified Ingestion Framework

**Status:** Draft v0.1  
**Last updated:** 2026-03-27  
**Scope:** Cross-component (Mosaic, formerly Hippo — ADR-0004 — + Cappella)

---

## 4.1 Motivation

Before this change, ingestion logic was split:
- Mosaic had `IngestionPipeline` with hardcoded `ingest_csv/json/jsonl` methods
- Mosaic had `ReferenceLoader` ABC for reference data plugins
- Cappella had its own `CSVAdapter`, `JSONAdapter`, `SQLAdapter`, `ExternalSourceAdapter` ABC
- Two separate pipeline implementations, two sets of field mapping logic, two error hierarchies

This creates maintenance burden, divergent behavior, and forces plugin authors to learn two different ABCs depending on whether they're writing a reference loader vs. an operational adapter.

## 4.2 The Unified Model

A single `EntityLoader` ABC lives in Mosaic core. Everything that loads data into Mosaic — reference loaders, Cappella adapters, CLI ingest, custom scripts — subclasses this one ABC.

```
EntityLoader (ABC, Mosaic core)
    │
    ├── ConfigurableLoader (Abstract, Mosaic core)
    │   │   Config-driven field_map + vocabulary_map
    │   │
    │   ├── CSVLoader (Concrete, Mosaic core)
    │   ├── JSONLoader (Concrete, Mosaic core)
    │   ├── SQLLoader (Concrete, Mosaic core, extras: mosaic[loaders-sql])
    │   └── EntityYAMLLoader (Concrete, Mosaic core)
    │       Loads structured entity YAML directly
    │
    ├── ReferenceLoader subclasses (Mosaic plugins)
    │   │   mosaic-reference-ensembl, mosaic-reference-bioconda, etc.
    │   │   May subclass ConfigurableLoader or EntityLoader directly
    │   └── Discovered via mosaic.reference_loaders entry points
    │
    └── Cappella adapter subclasses
        │   Complex integrations (STARLIMS API, paginated REST, SFTP)
        │   Subclass EntityLoader from Mosaic
        └── Discovered via cappella.adapters entry points
```

## 4.3 EntityLoader ABC

Lives in `mosaic.core.loaders.base`:

```python
class EntityLoader(ABC):
    """Base class for all data loading into Mosaic."""

    name: str                          # identifier, e.g. "csv", "ensembl", "starlims"
    entity_types: list[str]            # what this loader produces
    supports_incremental: bool = False

    @abstractmethod
    def fetch(self, since: datetime | None = None, **kwargs) -> Iterator[RawRecord]:
        """Pull records from the source."""
        ...

    @abstractmethod
    def transform(self, record: RawRecord) -> TransformedRecord:
        """Map source record to Mosaic entity schema."""
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

## 4.5 Built-in Loaders (Mosaic Core)

| Loader | Module | Base install | Notes |
|--------|--------|-------------|-------|
| `CSVLoader` | `mosaic.core.loaders.csv` | ✅ (stdlib csv) | File, HTTP URL, or stdin/bytes |
| `JSONLoader` | `mosaic.core.loaders.json` | ✅ (stdlib json) | JSONPath for nested records requires `mosaic[loaders-json]` |
| `SQLLoader` | `mosaic.core.loaders.sql` | `mosaic[loaders-sql]` | SQLAlchemy + read-only query validation |
| `EntityYAMLLoader` | `mosaic.core.loaders.entity_yaml` | ✅ (stdlib yaml) | Structured entity YAML, idempotent via external_id |

## 4.6 Dependency Extras (`pyproject.toml`)

```toml
[project.optional-dependencies]
loaders-sql = ["sqlalchemy>=2.0"]
loaders-json = ["jsonpath-ng>=1.6"]
loaders-all = ["sqlalchemy>=2.0", "jsonpath-ng>=1.6"]
```

CSV and EntityYAML have zero additional dependencies. JSON basic parsing needs no extras; JSONPath for nested records is an optional extra.

## 4.7 `mosaic ingest` CLI

The CLI becomes the manual entry point for the loader framework. No triggers, no automation — just run a loader once.

```bash
# Ingest from structured entity YAML
mosaic ingest --file entities.yaml

# Ingest from CSV with inline config
mosaic ingest --type csv --file donors.csv \
  --entity-type Donor \
  --external-id-field SUBJECT_ID \
  --field-map SUBJECT_ID=external_id SEX=sex DIAGNOSIS=diagnosis

# Ingest from CSV with a config file
mosaic ingest --type csv --file donors.csv --config donors_mapping.yaml

# Ingest from SQL (requires mosaic[loaders-sql])
mosaic ingest --type sql --config lims_query.yaml

# Dry run — show what would be created/updated without writing
mosaic ingest --file entities.yaml --dry-run
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

1. For each record, look up by `external_id` in Mosaic
2. If found and data identical → skip (unchanged)
3. If found and data differs → update
4. If not found → create + register external_id

This is the logic we just fixed in `_upsert_records` (catching `EntityNotFoundError` explicitly).

The `IngestPipeline` class (renamed from `IngestionPipeline`) orchestrates this loop for any `EntityLoader`. It moves from `mosaic.core.ingestion` to `mosaic.core.loaders.pipeline`.

## 4.9 What Changes in Mosaic

| Action | File/Module | Notes |
|--------|-------------|-------|
| **New** | `mosaic/src/mosaic/core/loaders/__init__.py` | Package exports |
| **New** | `mosaic/src/mosaic/core/loaders/base.py` | `EntityLoader`, `ConfigurableLoader`, `RawRecord`, `TransformedRecord` |
| **New** | `mosaic/src/mosaic/core/loaders/csv.py` | `CSVLoader` |
| **New** | `mosaic/src/mosaic/core/loaders/json.py` | `JSONLoader` |
| **New** | `mosaic/src/mosaic/core/loaders/sql.py` | `SQLLoader` |
| **New** | `mosaic/src/mosaic/core/loaders/entity_yaml.py` | `EntityYAMLLoader` |
| **New** | `mosaic/src/mosaic/core/loaders/pipeline.py` | `IngestPipeline` (refactored from `IngestionPipeline`) |
| **New** | `mosaic/cli/commands/ingest.py` | `ingest_entity_file()`, rewired CLI |
| **Modify** | `mosaic/src/mosaic/core/ingestion.py` | Keep `extract_fts_content`, `flatten_dict`; deprecate `IngestionPipeline` |
| **Modify** | `mosaic/pyproject.toml` | Add `loaders-sql`, `loaders-json` extras |
| **Remove** | `mosaic/src/mosaic/core/data_sources.py` | Replaced by loader config files |

## 4.10 What Changes in Cappella

| Action | Notes |
|--------|-------|
| **Modify** `cappella/src/cappella/adapters/base.py` | `ExternalSourceAdapter` subclasses `mosaic.core.loaders.base.EntityLoader` instead of its own ABC |
| **Modify** `cappella/src/cappella/adapters/csv_adapter.py` | Subclass `CSVLoader` from Mosaic, add Cappella-specific features (HTTP transport, `manual_upload` source) |
| **Modify** `cappella/src/cappella/adapters/json_adapter.py` | Subclass `JSONLoader` from Mosaic |
| **Modify** `cappella/src/cappella/adapters/sql_adapter.py` | Subclass `SQLLoader` from Mosaic |
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
- Tests Cappella adapter using Mosaic's `CSVLoader` against real Mosaic
- Tests that field_map and vocabulary_map from Mosaic core work when called from Cappella

**Updated Mosaic unit tests:**
- `mosaic/tests/core/test_loaders.py` replaces `test_ingestion.py` (same tests, new module paths)
- `mosaic/tests/cli/test_ingest.py` (already written, tests entity YAML ingest + idempotency)

## 4.13 Phased Implementation

**Phase 1 (Mosaic):** Create `loaders/` package, implement `EntityLoader` → `ConfigurableLoader` → `CSVLoader/JSONLoader/SQLLoader/EntityYAMLLoader` + `IngestPipeline`. Rewrite `mosaic ingest` CLI. All Mosaic tests green.

**Phase 2 (Cross-component contracts):** Write contract tests at monorepo root. RED until Cappella adopts.

**Phase 3 (Cappella):** Refactor adapters to subclass from Mosaic. Remove duplicate logic. All platform tests green.

**Phase 4 (Cleanup):** Deprecate `mosaic.core.ingestion.IngestionPipeline`. Update docs.
