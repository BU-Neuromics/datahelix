# BASS Platform — Architecture Design Index

**Status:** Living document  
**Last updated:** 2026-03-13  

This document records cross-cutting architectural decisions that apply to the BASS platform as a whole. Decisions that affect only a single component are recorded in that component's `design/INDEX.md`. This document takes precedence where conflicts exist.

---

## Document Map

| File | Topic | Status |
|---|---|---|
| `INDEX.md` (this file) | Platform-level decisions log and open questions | 🔄 Active |
| *(future)* `sec1_overview.md` | Platform vision, scope, and component relationships | ⬜ Not started |
| *(future)* `sec2_components.md` | Component responsibilities and boundaries | ⬜ Not started |
| *(future)* `sec3_integration.md` | Inter-component interfaces and contracts | ⬜ Not started |

---

## Key Decisions Log

### Component Responsibilities

| Decision | Choice | Rationale |
|---|---|---|
| Cappella's primary role | Integration and harmonization engine — the "conductor" that coordinates all data sources | Cappella ingests from external systems (HALO, STARLIMS, REDCap, partner omics, internal workflows), harmonizes data, and writes into Hippo. Not primarily a workflow executor (though workflow output ingestion is in scope). |
| Cappella's storage backend | Hippo exclusively — Cappella is stateless | Cappella does not own any data. All persistent state lives in Hippo. |
| Workflow execution scope | In scope for Cappella — pipeline runs are treated as a data source like any other | A workflow run takes Hippo entities as inputs, produces outputs (datafiles, QC metrics, derived entities), and Cappella captures inputs/outputs/provenance back into Hippo. The executor and the integration engine are unified. |
| Bridge scope | Deferred — not yet defined | Candidate role: federation layer between BASS instances (inter-institutional data sharing). Not a required component for single-institution deployments. |

### Adapter Boundaries (Hippo vs. Cappella)

| Decision | Choice | Rationale |
|---|---|---|
| External system adapter implementations | Live in Cappella | STARLIMS, HALO, REDCap, partner system connectors belong to the integration layer, not the storage layer. |
| `ExternalSourceAdapter` ABC | Stays in Hippo | Hippo defines the interface contract. Cappella (and third parties) provide implementations. Consistent with the `EntityStore` adapter pattern. |
| Field mapping and transformation config | Lives in Cappella adapter config | Hippo schema defines the *target* (canonical entity types and fields). Cappella adapter config defines the *mapping* from source system fields to Hippo fields. These are separate concerns in separate files. |
| Data cleaning and vocabulary normalization | Cappella adapter responsibility | Controlled vocabulary normalization (e.g., mapping variant spellings of anatomy labels to canonical FMA terms) is deployment-specific logic and belongs in the Cappella adapter layer, not Hippo. |
| Hippo external adapter stubs (STARLIMS, HALO, Donor DB) | To be removed from Hippo in a future spec update | Currently stubbed in `hippo/adapters/external/`. These implementations should migrate to Cappella. The `ExternalSourceAdapter` ABC remains in Hippo. |

### Reference Data and Canonical Identifiers

| Decision | Choice | Rationale |
|---|---|---|
| Reference ontology data (FMA, Ensembl, etc.) | Stored in Hippo as regular entities | `AnatomyTerm`, `Gene`, and similar reference types are defined in the schema config like any other entity type and loaded via batch ingestion at deployment time. |
| Canonical anatomy identifier | Foundational Model of Anatomy (FMA) | FMA is the authoritative reference for anatomy labels across the platform. |
| Canonical gene identifier | Ensembl gene ID | All gene references resolve to Ensembl IDs. Other identifiers (Entrez ID, gene symbol, RefSeq) are stored as ExternalIDs against the canonical `Gene` entity. |
| Gene identifier cross-referencing | Hippo `ExternalID` system (§3.4) | Entrez IDs, gene symbols, and other identifier systems map to a single canonical `Gene` entity UUID via Hippo's existing external ID machinery. No new mechanism required. |
| Cappella independence (reference data) | Hippo must be functional without Cappella | Cappella is a force multiplier on top of a working Hippo — not a prerequisite. A researcher can deploy Hippo standalone, load data via flat-file ingestion, and install reference data without touching Cappella. |

### Data Categories

Three distinct categories of data exist in a Hippo deployment. This distinction governs how data enters the system and who is responsible for maintaining it.

| Category | Owner | Mutability | How it enters Hippo | Examples |
|---|---|---|---|---|
| **Reference data** | External community authority | Read-only; updated by re-running a loader against a new release | `hippo reference install` via `ReferenceLoader` plugin | FMA anatomy terms, Ensembl genes, Gene Ontology terms, HPO, MONDO, NCBITaxon |
| **Config data** | Your institution; relatively static | Infrequent, admin-driven | Flat-file ingestion (`hippo ingest`) or schema enum values | Brain region dissection protocol, cohort definitions, tissue processing methods, lab-specific controlled vocabularies |
| **Operational data** | Your institution; actively growing | Continuous | Cappella adapters + workflow ingestion | Subjects, samples, datafiles, workflow runs, QC metrics |

**Decision rule for new data types:** *"Does an external organization release versioned updates to this data that any similar lab would use identically?"*
- **Yes** → reference loader (`hippo-reference-<name>` plugin)
- **No, institution-created and relatively static** → config data (flat-file ingestion or schema enum)
- **No, institution-created and operationally active** → operational data (Cappella adapter)

### Data Loading Tiers

| Tier | Mechanism | Cappella required? | Data category |
|---|---|---|---|
| 1 — Generic flat-file | `hippo ingest <file>` CLI (v0.1 scope) | No | Config data (and reference data if pre-converted to flat file) |
| 2 — Reference data | `hippo reference install <name>` + `hippo[references]` extra | No | Reference data |
| 3 — External systems | Cappella adapters | Yes | Operational data |

### Reference Loader Plugin System (MVP)

| Decision | Choice | Rationale |
|---|---|---|
| Plugin discovery mechanism | Python entry point group `hippo.reference_loaders` | Consistent with `hippo.storage_adapters` and `hippo.external_adapters`. Community packages auto-discovered after `pip install`. |
| Naming convention | `hippo-reference-<name>` (e.g. `hippo-reference-go`, `hippo-reference-ensembl`) | Matches `hippo-adapter-<name>` convention. Discoverable via PyPI search. |
| Schema ownership | Each `ReferenceLoader` ships a `schema_fragment()` | Loaders declare the entity types and relationships they create. Users do not need to hand-author reference entity schemas. |
| Install behavior | `hippo reference install <name>` merges the loader's schema fragment into the deployed schema and runs migrate automatically | Additive changes (new entity types, new fields, new enum values) are non-interactive. Structural changes prompt for confirmation. |
| User schema dependency declaration | `requires:` block in `schema.yaml` listing loader packages and minimum versions | Explicit dependency declaration. `hippo validate` fails fast with a clear error if a required loader is not installed. |
| Collision handling | `ConfigError` at startup if two installed loaders declare the same entity type name | Consistent with existing adapter conflict detection. |
| Update flow | `hippo reference update <name>` diffs new schema fragment against deployed version, runs migrate, reloads data | Reuses existing migration machinery entirely. |
| Extending loader-provided types | **Deferred — not in MVP** | Out of scope for initial implementation. Users cannot add fields to loader-provided entity types in v1. |

**`ReferenceLoader` ABC (MVP):**
```python
class ReferenceLoader(ABC):
    name: str           # e.g. "go", "fma", "ensembl"
    description: str

    @abstractmethod
    def versions(self) -> list[str]: ...          # available versions to install

    @abstractmethod
    def entity_types(self) -> list[str]: ...      # entity type names this loader creates

    @abstractmethod
    def schema_fragment(self) -> dict: ...        # entity + relationship definitions

    @abstractmethod
    def load(self, client: HippoClient, version: str, **kwargs) -> LoadResult: ...
```

**Example user `schema.yaml` referencing loader-provided types:**
```yaml
requires:
  - hippo-reference-ensembl>=GRCh38.109
  - hippo-reference-go>=2024-01-01

relationships:
  - name: annotated_with
    from: Gene       # provided by hippo-reference-ensembl
    to: GOTerm       # provided by hippo-reference-go
    cardinality: many-to-many
```

### Validation Architecture

| Decision | Choice | Rationale |
|---|---|---|
| Schema validation ownership | Hippo — built-in, always runs first | Structural constraints (required fields, type checking, enum values, ref integrity, cardinality) are schema-driven and enforced by Hippo regardless of write path. |
| Business rule validation ownership | `WriteValidator` plugin hook in Hippo, implemented by Cappella (and third parties) | Business rules are semantic/value-based (e.g., "can't link a Sample to a withdrawn Subject") and require reading current system state. They're deployment-specific but must be enforced on all write paths. |
| Enforcement point | Hippo write path — all writes (SDK, REST, batch ingest, Cappella) go through registered validators | Prevents bypass. Direct SDK or REST writes cannot circumvent business rules. Consistent with the principle that Hippo is the single source of truth. |
| Validator registration | Python entry point group `hippo.write_validators` | Consistent with adapter and reference loader plugin patterns. Auto-discovered at startup. No config file changes required. |
| Validator execution order | Schema validation (priority -1, always first) → registered validators (ordered by `priority` field) → commit + provenance | Structural rejection before semantic rejection. Atomic — any failure rolls back the entire transaction. |
| Standalone Hippo behavior | No business validators registered if no validator packages installed | Hippo without Cappella works correctly with schema validation only. Business rule enforcement is opt-in via installed plugins. |
| Validator scope | `entity_types` field on each validator — `None` means run for all; list means run only for named types | Validators only execute for relevant entity types. Keeps write performance predictable. |
| Failure behavior | Typed `ValidationError` raised with validator name and error list; REST layer returns HTTP 422; no partial writes | Caller always knows which validator rejected and why. Nothing is written on failure — no provenance event recorded. |
| Validator performance contract | Validators should be efficient; configurable per-validator timeout TBD | Validators run synchronously in the write transaction. Heavy cross-entity queries should be avoided or cached. |

**`WriteValidator` ABC:**
```python
class WriteValidator(ABC):
    name: str                          # used in error messages and logs
    entity_types: list[str] | None     # None = run for all entity types
    priority: int = 0                  # lower runs first; schema validation = -1

    @abstractmethod
    def validate(
        self,
        operation: WriteOperation,
        client: HippoClient            # read-only — writes raise an error
    ) -> ValidationResult: ...
```

**`WriteOperation` type:**
```python
@dataclass
class WriteOperation:
    kind: Literal["create", "update", "availability_change", "relationship"]
    entity_type: str
    entity_id: str
    proposed: dict      # new state being written
    existing: dict | None   # current state; None for creates
    actor: str
```

**Hippo spec impact:** This decision requires updates to the Hippo design spec — see Hippo spec update notes below.

### Search and Fuzzy Lookup

| Decision | Choice | Rationale |
|---|---|---|
| Fuzzy search abstraction | Implemented at the storage adapter level | The `EntityStore` ABC gains a `search` method. Each adapter implements fuzzy lookup using backend-appropriate mechanisms (SQLite FTS5, PostgreSQL pg_trgm, vector similarity, etc.). Cappella sees a uniform API regardless of backend. |
| Per-field search mode declaration | Declared in schema config per field (`search: fts \| embedding \| synonym`) | Intent is declared in the schema; implementation is the adapter's concern. Supports different strategies for different field types. |
| `ScoredMatch` response type | Core SDK type (adapter-agnostic) | Fields: `entity_id`, `entity_type`, `field`, `value`, `score` (0.0–1.0), `match_mode`. Cappella configures confidence thresholds per match mode in its adapter config. |
| Adapter capability declaration | Each adapter publishes supported search modes | Hippo validates at startup that schema-declared search modes are supported by the active adapter. Fails fast with a clear error on mismatch. Prevents silent degradation. |
| Resolution logic and confidence thresholds | Cappella adapter config | Hippo returns ranked candidates with scores. Cappella decides what to do with them (accept, flag for review, reject) based on deployment-specific thresholds. |

---

## Open Questions

| Question | Priority | Notes |
|---|---|---|
| Bridge: federation layer vs. other role? | Medium | Candidate: inter-BASS-instance data sharing for multi-institution deployments. Needs more design before a component spec can be started. |
| Platform name | Low | BASS is unsatisfactory. drylims is acceptable but not ideal. Revisit when higher-priority design work is complete. |
| Cappella config format | High | Adapter configs need to express more than field-to-field mappings — transformation pipelines with rules, vocabulary normalization, confidence thresholds. Format TBD. |
| Reference data versioning | Low | Resolved at the loader level — each loader version pins a reference ontology release. `hippo reference update` diffs schema and data. Internal tracking of installed loader name + version in `hippo_meta` table (sec3b). Detail TBD in Hippo sec5 (Ingestion). |
| Cappella trigger model | High | What initiates a Cappella sync? Options: event-driven (webhooks from source systems), scheduled (cron), manual, or pipeline-triggered. Likely all of the above — needs a unified model. |
| Multi-institution deployment model | Medium | If Bridge is a federation layer, what does a federated query look like? Does each institution run a full BASS stack? What data leaves the institution boundary? |
| Workflow executor integration | Medium | Does Cappella wrap an existing executor (Nextflow, Snakemake) or define its own? How are workflow definitions versioned and stored? |

---

## Component Responsibility Summary

| Component | Owns | Does not own |
|---|---|---|
| **Hippo** | Canonical entity schema, storage backends, `ExternalSourceAdapter` ABC, `EntityStore` ABC, `ReferenceLoader` ABC, provenance log, fuzzy search interface (SDK), `ScoredMatch` type, flat-file ingestion CLI, reference loader plugin system | External system connector implementations, field mapping config, harmonization logic, workflow execution |
| **Cappella** | External system adapter implementations, field mapping and transformation config, harmonization logic, vocabulary normalization, workflow orchestration and output ingestion | Storage, canonical schema definition, provenance, reference data loading |
| **Aperture** | User-facing query interface (CLI, web, API clients) | Business logic, storage, integration |
| **Bridge** | TBD — candidate: inter-BASS-instance federation | TBD |

---

## Pending Spec Updates

Decisions recorded here that require updates to existing or future component specs.

| Spec file | Change needed | Triggered by |
|---|---|---|
| `hippo/design/sec2_architecture.md` | Add `WriteValidator` ABC and `hippo.write_validators` entry point group to adapter pattern section; add `WriteOperation` and `ValidationResult` to package structure | Validation architecture decision |
| `hippo/design/sec2_architecture.md` | Add `EntityStore.search()` method and `ScoredMatch` type to adapter interface; add adapter capability declaration mechanism | Fuzzy search decision |
| `hippo/design/sec2_architecture.md` | Add `ReferenceLoader` ABC and `hippo.reference_loaders` entry point group to plugin system section | Reference loader plugin system decision |
| `hippo/design/sec2_architecture.md` | Remove `ExternalSourceAdapter` concrete stubs (STARLIMS, HALO, Donor DB) from Hippo package structure — ABC stays, implementations move to Cappella | Adapter boundary decision |
| `hippo/design/sec3_data_model.md` | Add `search` field declaration to schema config field type table | Fuzzy search decision |
| `hippo/design/sec3_data_model.md` | Add `requires:` block to schema config format | Reference loader plugin system decision |
| `hippo/design/sec4_api_layer.md` | *(not started)* Include fuzzy search endpoint (`?q=&match=`) and `ScoredMatch` response type | Fuzzy search decision |
| `hippo/design/sec5_ingestion.md` | *(not started)* Include `hippo reference install/update/list` CLI commands; `ReferenceLoader` lifecycle; reference loader version tracking in `hippo_meta` | Reference loader plugin system decision |
| `hippo/design/INDEX.md` | Add decisions from today's session to Hippo key decisions log | All Hippo-touching decisions |
| `cappella/design/` | *(not started)* All sections — Cappella design spec not yet written | Cappella architecture session |

---

## Design Session Notes

**2026-03-13** — Initial platform architecture session (Adam + Stanley).  
Topics covered: Cappella scope and conductor metaphor, adapter boundary between Hippo and Cappella, field mapping ownership, reference/config/operational data category distinction, data loading tiers, reference loader plugin system (MVP scope), fuzzy search abstraction, gene/anatomy canonical identifiers, Cappella-independence principle, WriteValidator plugin hook for business rule enforcement.
