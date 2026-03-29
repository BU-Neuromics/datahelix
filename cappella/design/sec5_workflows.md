# Section 5: Collection Resolution Workflow

**Status:** Draft v0.1  
**Last updated:** 2026-03-25

> Note: This section was originally titled "Workflow Execution" in the spec outline.
> After design sessions, it became clear that Cappella does not own workflow execution —
> that is Canon's domain. This section covers Cappella's **collection resolution workflow**:
> the end-to-end process of translating a user request into a HarmonizedCollection.
> See Canon design for CWL execution details.

---

## 5.1 Resolution Workflow Overview

```
User request (via Aperture, CLI, or Composer)
    │
    ▼
POST /resolve
{entity_type, criteria, parameters, selection}
    │
    ▼
Step 1: Parse & validate request
    │  Validate entity_type exists in Hippo schema
    │  Validate criteria fields exist in referenced entity schemas
    │
    ▼
Step 2: Cohort construction (Hippo queries)
    │  Walk entity graph bottom-up using criteria
    │  Donor → Sample → SequencingDataset (inferred from schema references)
    │
    ▼
Step 3: Dataset selection
    │  Apply SelectionStrategy per sample
    │  Apply QC filters from request
    │  Record which datasets were selected and why
    │
    ▼
Step 4: Canon delegation (per selected dataset)
    │  canon.resolve(entity_type, {**parameters, dataset_id: id})
    │  Collect resolved URIs and Canon decisions
    │  Collect unresolved items with structured reasons
    │
    ▼
Step 5: Assemble HarmonizedCollection
    │  resolved[], unresolved[], provenance{}
    │
    ▼
Return to caller
```

---

## 5.2 Schema-Driven Entity Traversal

Cappella infers entity traversal paths from the Hippo schema's `references:` declarations rather than hardcoding paths. This means adding a new entity type to the schema automatically makes it traversable without Cappella code changes.

**Example traversal for `GeneCounts` request with `criteria: {donor.diagnosis: CTE, sample.tissue: DLPFC}`:**

```
GeneCounts references SequencingDataset
SequencingDataset references Sample
Sample references Donor

Traversal (bottom-up):
1. query("Donor", {diagnosis: "CTE"}) → [D001, D002, D003]
2. query("Sample", {tissue: "DLPFC", donor_id: in(D001,D002,D003)}) → [S001, S002, S004]
3. query("SequencingDataset", {assay: "RNASeq", sample_id: in(S001,S002,S004)}) → [DS001, DS002, DS003, DS005]
```

Schema-driven traversal is the only supported mode in Cappella v0.1. It requires `HippoClient.schema_references(entity_type)` — implemented in Hippo v0.4 and available now. This method reads `FieldDefinition.references` from the already-loaded schema and returns reference edges. Schema YAML must declare `references: {entity_type: <name>}` on foreign-key fields for traversal to work. `EntityTraversal` calls `schema_references()` at runtime to infer traversal paths from dot-notation criteria like `donor.diagnosis` and `sample.tissue`.

---

## 5.3 Selection Strategies

When a sample has multiple candidate datasets, a `SelectionStrategy` picks one.

### Built-in Strategies

#### `most_recent`
Select the dataset with the highest `created_at` timestamp after applying QC filters.

```yaml
selection:
  strategy: most_recent
  filters:
    dataset.qc.min_reads: 1000000
    dataset.qc.pct_mapped_min: 0.70
```

#### `highest_quality`
Select the dataset with the best value for a declared quality field.

```yaml
selection:
  strategy: highest_quality
  quality_field: qc.pct_mapped
  filters:
    dataset.qc.min_reads: 1000000
```

#### `explicit`
Use an explicit list of entity IDs. All samples not covered by the list fall through to `most_recent`. Useful when a researcher wants to pin specific datasets for a reproducible analysis.

```yaml
selection:
  strategy: explicit
  overrides:
    S001: DS001-uuid
    S003: DS003-v2-uuid
  fallback: most_recent
```

#### `single_only`
Raise a `MultipleDatasetError` if any sample has more than one candidate after filters. Useful for strict reproducibility — fail loudly rather than silently picking one.

### Custom Strategies

Custom strategies are discoverable via `cappella.selection_strategies` entry points:

```toml
[project.entry-points."cappella.selection_strategies"]
lab_standard = "my_lab_cappella:LabStandardStrategy"
```

---

## 5.4 Partial Failure Handling

Cappella never aborts a resolution run due to partial failures. Items that cannot be resolved are collected in the `unresolved` list with structured reasons:

| Reason | Description |
|--------|-------------|
| `no_dataset` | No SequencingDataset found for this sample |
| `multiple_datasets_no_selection` | Multiple datasets found and `single_only` strategy selected |
| `qc_filter_failed` | Dataset exists but does not pass QC filters |
| `canon_no_rule` | Canon has no rule to produce the requested entity type |
| `canon_error` | Canon returned an unexpected error |
| `canon_timeout` | Canon did not respond within the configured timeout |

A resolution run with 3/4 samples resolved and 1 unresolved is a valid result, not a failure. The caller decides whether 75% resolution is acceptable for their use case.

---

## 5.5 Resolution Job API

`POST /resolve` validates the request immediately and either rejects it or accepts it. It never blocks waiting for resolution to complete.

```
POST /resolve
  → 400 Bad Request    invalid entity_type, unknown criteria field, malformed parameters
  → 422 Unprocessable  valid request but zero samples match the criteria
  → 202 Accepted       request queued successfully
```

202 response:
```json
{
  "run_id": "uuid-run-789",
  "status": "queued",
  "poll_url": "/resolve/uuid-run-789"
}
```

The client polls `GET /resolve/{run_id}` for status:

```json
// While running — live progress
GET /resolve/uuid-run-789
→ 200 OK
{
  "run_id": "uuid-run-789",
  "status": "running",
  "started_at": "2026-03-25T21:27:00Z",
  "samples_total": 47,
  "samples_resolved": 12,
  "samples_failed": 0
}

// On completion
→ 200 OK
{
  "run_id": "uuid-run-789",
  "status": "complete",
  "started_at": "2026-03-25T21:27:00Z",
  "finished_at": "2026-03-25T21:31:22Z",
  "collection": { ... HarmonizedCollection ... }
}

// On failure (e.g. Canon unreachable for all samples)
→ 200 OK
{
  "run_id": "uuid-run-789",
  "status": "failed",
  "error": "Canon service unavailable after 3 retries"
}
```

The `samples_resolved` counter increments as Canon returns results, enabling Aperture/Composer to display live progress without waiting for completion.

The CLI polls internally and blocks until complete, displaying a progress indicator:

```bash
cappella resolve \
  --entity-type GeneCounts \
  --criteria "donor.diagnosis=CTE" "sample.tissue=DLPFC" \
  --parameters genome=GRCh38 \
  --output my_collection.json
# Resolving 47 samples... [12/47] ████░░░░░░ 26%
# Complete. 45 resolved, 2 unresolved. Written to my_collection.json

cappella resolve ... --run-id uuid-run-789  # Attach to existing run
```

---

## 5.6 Resolution Run Caching (v0.2)

**Opinion (mark for review):** In v0.2, completed `HarmonizedCollection` results are stored as `ResolutionRun` Hippo entities. Identical requests (same entity_type + criteria + parameters + selection + schema version) return a cached result. Cache TTL is configurable. This enables Composer to reference past resolution runs by ID rather than re-resolving, which is important for reproducibility — the exact collection used for a published analysis is a permanent Hippo record.

---

## 5.7 CLI Interface

Cappella provides a CLI for interactive use:

```bash
# Resolve a collection
cappella resolve \
  --entity-type GeneCounts \
  --criteria "donor.diagnosis=CTE" "sample.tissue=DLPFC" \
  --parameters genome=GRCh38 \
  --selection most_recent \
  --output json > my_collection.json

# Run an immediate ingest
cappella ingest starlims --incremental

# Fire a trigger manually
cappella trigger run nightly_starlims_sync

# Check status
cappella status

# Show reconciliation findings
cappella findings --entity-type Donor --check field_conflict
```
