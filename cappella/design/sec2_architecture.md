# Section 2: Architecture

**Status:** Draft v0.1  
**Last updated:** 2026-03-25

---

## 2.1 Architectural Overview

Cappella is structured as five cooperating layers, all stateless, all writing exclusively to Hippo:

```
┌─────────────────────────────────────────────────────────────┐
│  REST API / CLI                                             │
│  /resolve  /ingest  /triggers/{name}/run  /status          │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
   ┌─────────────┐ ┌──────────┐ ┌──────────────────┐
   │  Collection │ │  Ingest  │ │  Trigger Engine  │
   │  Resolver   │ │ Pipeline │ │ (schedule/manual/│
   │             │ │          │ │  webhook/event)  │
   └──────┬──────┘ └────┬─────┘ └────────┬─────────┘
          │             │                │
          ▼             ▼                ▼
   ┌─────────────────────────────────────────────────┐
   │  Adapter Registry                               │
   │  ExternalSourceAdapter plugins (STARLIMS, HALO) │
   │  Canon client (artifact resolution)             │
   └──────────────────────┬──────────────────────────┘
                          │
                          ▼
   ┌─────────────────────────────────────────────────┐
   │  HippoClient                                    │
   │  All reads and writes go through here           │
   └─────────────────────────────────────────────────┘
```

---

## 2.2 Adapter Registry

### ExternalSourceAdapter ABC

Defined in Hippo (`hippo.core.adapters`), implemented in Cappella. Each adapter handles one external system.

```python
class ExternalSourceAdapter(ABC):
    name: str                          # "starlims", "halo", "redcap"
    entity_types: list[str]            # ["Donor", "Sample"] — what this adapter produces
    supports_incremental: bool = False # True if adapter can pull only changed records

    @abstractmethod
    def fetch(self, since: datetime | None = None) -> Iterator[RawRecord]:
        """Pull records from the external system. since=None means full sync."""
        ...

    @abstractmethod
    def transform(self, record: RawRecord) -> TransformedRecord:
        """Map external record to Hippo entity schema.
        Returns: entity_type, data dict, external_id, source_system."""
        ...

    def validate(self, record: TransformedRecord, hippo_client: HippoClient) -> list[str]:
        """Optional cross-record validation. Returns list of error messages."""
        return []
```

The `transform()` step is where field mapping, vocabulary normalization, and schema conformance happen. Each adapter ships its own `transform()` — no shared transformation pipeline is needed at the Cappella level.

### Adapter Discovery

Adapters are discovered via the `cappella.adapters` entry point group:

```toml
# pyproject.toml of cappella-adapter-starlims:
[project.entry-points."cappella.adapters"]
starlims = "cappella_starlims:STARLIMSAdapter"
```

Cappella's `AdapterRegistry` discovers and instantiates adapters at startup.

### Canon Client

The Canon client is registered in the adapter registry as a special non-ingestion adapter — it resolves artifacts rather than ingesting structured records. The `CollectionResolver` accesses it directly (see §2.4).

---

## 2.3 Ingest Pipeline

Each ingest run follows a fixed pipeline:

```
fetch(since) → [RawRecord, ...]
    │
    ▼
transform(record) → TransformedRecord{entity_type, data, external_id, source}
    │
    ▼
validate(record, hippo) → [] or [errors...]
    │ (stop if errors)
    ▼
upsert(entity_type, data, external_id, source)
    → HippoClient.create() if new
    → HippoClient.update() if changed
    → skip if identical
    │
    ▼
record provenance event on entity
    {source: "starlims", sync_run_id: "...", fetched_at: "..."}
```

### Upsert Identity Resolution

Priority:
1. **Explicit UUID** — if the external record carries a Hippo entity UUID
2. **ExternalID lookup** — `hippo.get_entity_by_external_id(system, external_id)`
3. **Create new** — if no match found

This is the same identity resolution Hippo's ingestion pipeline uses. Cappella delegates to `HippoClient` for all writes.

### Conflict Detection

When `transform()` produces data that differs from the existing Hippo entity for a matched ExternalID, Cappella applies conflict resolution:

- **Trusted source wins** — each adapter declares `trust_level: int`; higher trust overwrites lower
- **Last-write wins** — if trust levels are equal, most recent sync wins
- **Manual review flag** — if declared fields conflict across same-trust sources, flag the entity for reconciliation review

Conflicts are recorded as structured `HarmonizationConflict` provenance events on the entity, not silently overwritten.

---

## 2.4 Collection Resolver

The collection resolver is Cappella's highest-value capability — translating a high-level user request into a fully-resolved set of entities.

### Resolution Request

```json
POST /resolve
{
  "entity_type": "GeneCounts",
  "criteria": {
    "donor.diagnosis": "CTE",
    "sample.tissue": "DLPFC",
    "dataset.assay": "RNASeq"
  },
  "parameters": {
    "genome": "GRCh38",
    "annotation": "ref:GeneAnnotation{source=ensembl, release=110}"
  },
  "selection": {
    "strategy": "most_recent",
    "filters": {"dataset.qc.min_reads": 1000000}
  }
}
```

### Resolution Steps

**Step 1: Entity traversal (Hippo queries)**

Cappella walks the entity graph bottom-up using the `criteria` filters:
```
Donor{diagnosis=CTE}
  → Sample{tissue=DLPFC, donor_id ∈ matching_donors}
    → SequencingDataset{assay=RNASeq, sample_id ∈ matching_samples}
```

The traversal path is inferred from the Hippo schema's `references:` declarations. Cappella doesn't need hardcoded traversal logic — it reads the schema graph.

**Step 2: Selection logic**

When a sample has multiple candidate datasets (multiple sequencing runs, replicates), selection logic picks one per sample:

```python
class SelectionStrategy(ABC):
    @abstractmethod
    def select(self, candidates: list[Entity], filters: dict) -> Entity | None:
        ...
```

Built-in strategies:
- `most_recent` — highest `created_at` after applying filters
- `highest_quality` — sort by declared quality field (configurable per entity type)
- `explicit` — caller provides an explicit list of entity IDs to use

Selection strategies are pluggable via `cappella.selection_strategies` entry point. Labs can implement custom strategies (e.g., "prefer datasets from core facility X over resubmissions").

**Step 3: Canon delegation**

For each selected dataset, Cappella calls `canon.resolve()` for the requested `entity_type`:

```python
for dataset in selected_datasets:
    try:
        uri = canon_client.resolve(
            entity_type=request.entity_type,
            params={**request.parameters, "dataset_id": dataset.id}
        )
        resolved.append(ResolvedItem(sample=dataset.sample_id, uri=uri, status="resolved"))
    except CanonNoRuleError:
        unresolved.append(UnresolvedItem(sample=dataset.sample_id, reason="no_rule"))
    except CanonResolveError as e:
        unresolved.append(UnresolvedItem(sample=dataset.sample_id, reason="canon_error", detail=str(e)))
```

Cappella never raises on partial failure — it collects all resolved and all unresolved items and returns both.

**Step 4: HarmonizedCollection response**

See §1.5 for the full format. The collection includes:
- All resolved entities with URIs and Canon decision (REUSE/FETCH/BUILD)
- All unresolved items with structured reasons
- Full provenance (versions, genome build entity, selection criteria)

---

## 2.5 Trigger Engine

Triggers are the mechanism by which Cappella executes ingest and resolution operations automatically.

### Trigger Types (v0.1)

| Type | Mechanism | Use case |
|------|-----------|----------|
| `schedule` | Cron expression | Nightly STARLIMS sync, weekly full reconciliation |
| `manual` | API call | User-initiated ingest or resolution |
| `internal_event` | Named event emitted by another action | Chain: sample_created → trigger alignment resolution |

### Trigger Configuration (`cappella.yaml`)

```yaml
triggers:
  - name: nightly_starlims_sync
    type: schedule
    schedule: "0 2 * * *"    # 2 AM daily
    action:
      type: ingest
      adapter: starlims
      incremental: true
    on_success:
      emit: starlims_sync_complete

  - name: resolve_on_new_sample
    type: internal_event
    event: starlims_sync_complete
    action:
      type: resolve
      entity_type: AlignmentFile
      criteria:
        sample.tissue: DLPFC
      parameters:
        genome: GRCh38
```

### Trigger Action Types

| Action | Description |
|--------|-------------|
| `ingest` | Run an adapter's fetch/transform/upsert pipeline |
| `resolve` | Run collection resolution, optionally store result as ResolutionRun entity |
| `reconcile` | Run inconsistency detection for specified entity types |
| `notify` | Send a notification (Hippo event, webhook, email) |

### Action Chaining

Actions emit named internal events (`emit:`) that other triggers subscribe to. This is simple event-driven composition — not a DAG scheduler. Cycles are detected at config validation time and rejected with an error.

---

## 2.6 Reconciliation Engine

Reconciliation detects and surfaces inconsistencies across sources without automatically resolving them (resolution is a human decision for ambiguous conflicts).

### Checks (v0.1)

| Check | Description |
|-------|-------------|
| `missing_entity` | Entity referenced in external system has no Hippo record |
| `stale_entity` | Hippo entity not updated in external system within expected window |
| `field_conflict` | Same entity field has different values in two trusted sources |
| `broken_reference` | Entity has a `references:` field pointing to a nonexistent entity |
| `missing_artifact` | Entity has no associated file artifact where one is expected |

Each check produces a structured `ReconciliationFinding` — not an error, not an automatic fix. Findings are queryable from Hippo and surfaced in Aperture.

### Reconciliation Run

```
POST /reconcile
{
  "entity_types": ["Donor", "Sample"],
  "adapters": ["starlims", "redcap"],
  "checks": ["field_conflict", "missing_entity"]
}
```

Returns a list of `ReconciliationFinding` objects. Each finding includes the entity ID, field, source A value, source B value, and a suggested resolution action (human review, trust source A, trust source B).

---

## 2.7 Provenance Model

Every Cappella write to Hippo carries a structured `context` on the provenance event:

```json
{
  "cappella_version": "0.1.0",
  "source": "starlims",
  "sync_run_id": "uuid-run-123",
  "adapter_version": "1.2.0",
  "fetched_at": "2026-03-25T17:30:00Z",
  "trigger": "nightly_starlims_sync",
  "selection_strategy": "most_recent"
}
```

This mirrors the pattern established in Hippo's provenance event model and is consistent with the context Cappella receives from Canon for artifact entities.

---

## 2.8 API Surface (v0.1)

| Endpoint | Description |
|----------|-------------|
| `POST /resolve` | Submit a collection resolution request |
| `GET /resolve/{run_id}` | Get status/result of a resolution run |
| `POST /ingest` | Trigger an immediate ingest for a named adapter |
| `GET /ingest/{run_id}` | Get status of an ingest run |
| `POST /triggers/{name}/run` | Manually fire a named trigger |
| `GET /triggers` | List all configured triggers and their last-run status |
| `POST /reconcile` | Run reconciliation checks |
| `GET /findings` | Query reconciliation findings |
| `GET /status` | Cappella health, connected adapters, Hippo version |

---

## 2.9 Deployment Model

Cappella is a stateless Python service. It connects to:
- A running Hippo instance (via `HippoClient`)
- A running Canon instance (via `CanonClient` HTTP or in-process)
- External systems as configured in adapters

No Cappella-local database. All persistent state — sync history, reconciliation findings, resolution runs — is stored as Hippo entities.

Cappella can be run as:
- A standalone CLI tool (`cappella resolve`, `cappella ingest starlims`)
- A REST service (`cappella serve`)
- Embedded as a Python library in Composer or other tools

---

## 2.10 Open Questions for v0.1

| Question | Priority | Notes |
|----------|----------|-------|
| Schema-driven traversal | **Resolved ✅** | `HippoClient.schema_references(entity_type)` implemented in Hippo v0.4. Reads `FieldDefinition.references` from schema. REST: `GET /schemas/{entity_type}/references`. Cappella's `EntityTraversal` calls it at runtime. Schema YAML must declare `references: {entity_type: <name>}` on foreign-key fields. |
| Selection strategy config syntax | High | How are per-entity-type quality fields declared? In cappella.yaml or in the Hippo schema? |
| Canon client transport | Medium | In-process (import canon directly) or HTTP (call Canon REST API)? In-process is simpler for v0.1; HTTP required for distributed deployment. |
| ResolutionRun entity storage | Medium | Should every `POST /resolve` create a `ResolutionRun` entity in Hippo? Useful for audit but adds write overhead. Deferred to v0.2. |
| Webhook triggers | Medium | Deferred to v0.2 — requires endpoint registration, signature verification, retry logic. |
| Hippo poll triggers | Medium | Deferred to v0.2 — requires efficient change detection (polling `updated_at` index). |
