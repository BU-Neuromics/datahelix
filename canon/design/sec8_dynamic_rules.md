# Section 8: Dynamic Rule Registration and Convention-Based Output Mapping

**Status:** Design complete — v0.2/v0.3 target  
**Last updated:** 2026-03-25

---

## Motivation

`canon_rules.yaml` is a static file loaded at startup. Bespoke research analyses (custom DESeq2 comparisons, novel clustering algorithms, one-off QC pipelines) cannot be registered without editing the file and restarting Canon. This blocks researchers from using Canon for ad-hoc analysis while retaining the reproducibility and provenance guarantees that make Canon valuable.

Dynamic rule registration via API solves this: a researcher (or Composer) can register a new production rule — including a CWL workflow — at runtime. Canon validates the contract, stores the rule, and it is immediately available for resolution.

---

## Design Principles

1. **Hippo schema is the contract.** Entity types and their fields are defined in the Hippo schema *before* a rule that produces them is registered. Canon validates CWL outputs against the schema — no separate sidecar contract needed for well-typed entities.

2. **Static rules and dynamic rules are composable.** `canon_rules.yaml` provides stable lab-standard pipelines. Dynamic rules extend the registry at runtime for bespoke analyses. Resolution logic is identical for both.

3. **CWL structure encodes Hippo mapping.** CWL record-typed outputs map to Hippo entities by convention or explicit `from_output` declaration. No separate sidecar file required for single-type or well-named multi-type outputs.

4. **Rules are first-class Hippo entities.** Dynamic rules are stored as `ProductionRuleDefinition` entities in Hippo (or a Canon-local SQLite store), with full provenance: who registered, when, what CWL version/hash.

---

## Convention-Based Output Mapping

### Single entity output (simplest case)

CWL output field names match Hippo entity field names directly. The entity type is declared once in the rule, not the CWL:

```yaml
# CWL outputs (deseq2.cwl)
outputs:
  uri:               # → DifferentialExpression.uri
    type: File
  n_significant:     # → DifferentialExpression.n_significant
    type: int
  contrast:          # → DifferentialExpression.contrast
    type: string
```

Rule registration:
```json
{
  "name": "deseq2_contrast",
  "produces": {"entity_type": "DifferentialExpression", "match": {"contrast": "{contrast}"}},
  "requires": [{"ref": "CountsMatrix{id: \"{counts_matrix_id}\"}"}],
  "execute": {"cwl": "https://github.com/mylab/deseq2.cwl"}
}
```

### Multi-entity output via `from_output`

When a CWL produces multiple entities — even two of the same type — each top-level CWL output is a typed record. The rule declares explicit `from_output` mappings:

```yaml
# CWL outputs (deseq2_with_qc.cwl)
outputs:
  deseq2_result:
    type:
      type: record
      fields:
        uri: File
        contrast: string
        n_significant: int

  qc_report:
    type:
      type: record
      fields:
        uri: File
        n_reads_total: int
        pct_mapped: float
```

Rule registration:
```json
{
  "name": "deseq2_with_qc",
  "produces": [
    {
      "entity_type": "DifferentialExpression",
      "from_output": "deseq2_result",
      "match": {"contrast": "{contrast}", "counts_matrix_id": "{counts_matrix_id}"}
    },
    {
      "entity_type": "QCReport",
      "from_output": "qc_report",
      "match": {"counts_matrix_id": "{counts_matrix_id}"}
    }
  ],
  "execute": {"cwl": "https://..."}
}
```

### Multiple outputs of the same entity type

When a CWL produces two outputs of the same entity type (e.g., two `CountsMatrix` with different filtering criteria), the name-based convention fails and `from_output` is required:

```json
"produces": [
  {
    "entity_type": "CountsMatrix",
    "from_output": "counts_unfiltered",
    "match": {"filtering": "none", "cohort_id": "{cohort_id}"}
  },
  {
    "entity_type": "CountsMatrix",
    "from_output": "counts_filtered",
    "match": {"filtering": "low_count_removal", "cohort_id": "{cohort_id}"}
  }
]
```

The `from_output` approach is always valid and unambiguous. The name convention is a convenience for the simple single-entity case.

---

## Nondeterministic / Array Outputs

CWL supports array-typed outputs — a workflow can produce `File[]` or `record[]` when the number of outputs is not known at workflow-authoring time. A clustering algorithm that produces N clusters (N unknown until runtime) is a natural example.

CWL representation:
```yaml
outputs:
  cluster_files:
    type:
      type: array
      items:
        type: record
        fields:
          uri: File
          cluster_id: string
          n_members: int
          algorithm: string
```

Canon's ingestion model for array outputs:

```json
{
  "entity_type": "ClusterResult",
  "from_output": "cluster_files",
  "array_mode": "one_per_item",
  "match": {
    "algorithm": "{algorithm}",
    "counts_matrix_id": "{counts_matrix_id}",
    "cluster_id": "{cluster_id}"    ← from each array item's fields
  }
}
```

`array_mode: "one_per_item"` tells Canon to create one Hippo entity per array element, using the per-item record fields for identity. This is a natural fit for clustering: 12 clusters → 12 `ClusterResult` entities in Hippo, each with their own `uri`, `cluster_id`, and `n_members`.

**Design constraint:** Array outputs require that each array item has a unique identity-field combination. Canon raises `CanonIngestionError` if two items in the array would map to the same Hippo entity spec.

**Array outputs and resolution:** Can Canon *produce* array-output entities via `canon.resolve()`? For v0.1 dynamic rules, the answer is **yes but with a twist** — `canon.resolve()` returns a single URI. For array outputs, Canon should expose a `canon.resolve_all()` (or `canon.query_collection()`) that returns all entities matching a partial spec. Composer calls `resolve_all("ClusterResult", {counts_matrix_id: X, algorithm: "leiden"})` and gets back a list of all cluster entities. This is deferred to Canon v0.3.

**Scope boundary for Composer v0.1:** Array-output workflows are supported by Canon's ingestion layer from the start (it's just a loop over items). The `resolve_all()` query interface is the v0.3 addition. For v0.1, Composer can query Hippo directly for all `ClusterResult` entities matching a given `counts_matrix_id`.

---

## Dynamic Rule Registration API

### Endpoint

```
POST /api/v1/rules
Authorization: Bearer <token>
Content-Type: application/json
```

### Payload

```json
{
  "name": "my_analysis_rule",
  "produces": [
    {
      "entity_type": "DifferentialExpression",
      "from_output": "deseq2_result",     // optional; inferred by convention if omitted
      "match": {
        "contrast": "{contrast}",
        "counts_matrix_id": "{counts_matrix_id}"
      }
    }
  ],
  "requires": [
    {"ref": "CountsMatrix{id: \"{counts_matrix_id}\"}"}
  ],
  "execute": {
    "cwl_url": "https://github.com/mylab/workflows/deseq2.cwl",
    // OR:
    "cwl_content": "<base64-encoded CWL>",   // v0.3
    "cwl_hash": "sha256:abc123..."           // optional integrity check
  },
  "description": "Human-readable description of what this rule does",
  "tags": ["rnaseq", "deseq2", "differential-expression"]
}
```

### Validation steps (Canon on receipt)

1. Parse and validate CWL with `cwltool --validate`
2. Verify each `entity_type` in `produces` exists in the connected Hippo schema
3. Verify CWL output names (or `from_output` targets) exist in the CWL outputs
4. Verify CWL output record fields are a subset of the Hippo entity's fields
5. Verify `uri: File` is present for file-backed entities
6. Verify identity fields in `match` are covered by CWL output fields
7. Check for rule name uniqueness (reject or version-bump on conflict)

### Storage

Dynamic rules are stored as `ProductionRuleDefinition` entities in Hippo (preferred) or Canon-local SQLite. Hippo storage gives provenance for free — who registered, when, which CWL version. Canon queries dynamic rules after checking static `canon_rules.yaml`.

### CWL storage

- **v0.2:** `cwl_url` only — Canon fetches and caches the CWL at registration time; content-addressed by hash
- **v0.3:** `cwl_content` inline (base64) — Canon stores the CWL bytes in Hippo or a local artifact store

---

## Phased Implementation

### Canon v0.2
- Dynamic rule registration API (URL-based CWL only)
- Convention-based single-entity output mapping
- `from_output` for multi-entity / same-type disambiguation
- `ProductionRuleDefinition` entity type in Canon Hippo reference schema

### Canon v0.3
- Inline CWL submission (base64 upload)
- Array-typed output ingestion (`array_mode: one_per_item`)
- `canon.resolve_all()` / `canon.query_collection()` for array-output entities
- Security controls: Docker image allowlist, resource limits on submitted workflows

---

## Open Questions

| Question | Priority | Notes |
|----------|----------|-------|
| Rule versioning | Medium | What happens when the same rule name is re-registered with updated CWL? Auto-version-bump? Replace? |
| Rule scoping | Medium | Lab-global rules vs. user-private rules? Or purely by Hippo auth? |
| Rule deprecation | Low | How are dynamic rules disabled or removed? Entity `supersede_entity`? |
| CWL input/output type coercion | Low | CWL `int` → Hippo `string` field: reject or coerce? |
| `resolve_all()` pagination | Low | Array outputs for large cohorts could return thousands of entities |
