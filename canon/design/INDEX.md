# Canon — Design Specification Index

**Codename:** Canon  
**Component:** Semantic Artifact Resolver  
**Version:** 0.1-draft  
**Last updated:** 2026-03-23

---

## Document Map

| File | Section | Status | Notes |
|---|---|---|---|
| `sec1_overview.md` | 1. Overview & Scope | 🔄 In progress | |
| `sec2_architecture.md` | 2. Architecture | ⬜ Not started | |
| `sec3_rules_dsl.md` | 3. Canon Rules DSL | ⬜ Not started | |
| `sec3b_cwl_integration.md` | 3b. CWL Integration | ⬜ Not started | |
| `sec4_resolution_algorithm.md` | 4. Resolution Algorithm | ⬜ Not started | |
| `sec5_executor_adapters.md` | 5. Executor Adapters | ⬜ Not started | |
| `sec6_hippo_integration.md` | 6. Hippo Integration | ⬜ Not started | |
| `sec7_nfr.md` | 7. Non-Functional Requirements | ⬜ Not started | |
| `reference_canon_yaml.md` | Reference: canon.yaml schema | ⬜ Not started | |
| `reference_canon_rules_yaml.md` | Reference: canon_rules.yaml schema | ⬜ Not started | |
| `appendix_a_rnaseq_example.md` | Appendix A: RNA-seq worked example | ⬜ Not started | |

---

## Key Decisions Log

### Component Identity

| Decision | Choice | Rationale |
|---|---|---|
| Canon's role | Semantic artifact resolver — "give me this artifact, I'll find it or make it" | Narrow, composable, testable |
| Scope boundary | One operation: `canon get <spec>` → URI. No cohort logic, no set management. | Complexity cap; Cappella owns the set-level logic |
| Workflow language | CWL (Common Workflow Language v1.2) | Mature standard, schematic/execution separation, community tooling, visual builder ecosystem |
| Execution delegation | CWL executor adapters (cwltool, Toil, Nextflow CWL mode) | Canon never implements execution; delegates entirely to CWL runners |
| Storage | Stateless — Hippo is the sole persistent store | Consistent with platform adapter pattern |
| Hippo dependency | Required — Canon cannot function without a Hippo instance | Canon reads registry (does this exist?) and writes results (here's what I made) |

### Resolution Model

| Decision | Choice | Rationale |
|---|---|---|
| Resolution strategy | Lazy recursive — resolve one artifact at a time, walk dependencies on demand | Simpler than upfront DAG planning; avoids building plan objects |
| Artifact identity | Entity type + metadata parameter set (exact match for v0.1) | Unambiguous; maps directly to Hippo entity queries |
| Reuse check | Query Hippo before any execution | Hippo is the authoritative registry of what has been computed |
| Dependency resolution | Canon calls itself recursively for required inputs | Each `requires:` entry in a Canon rule is resolved the same way as the top-level request |
| Cycle detection | Required — Canon must detect circular rule dependencies | Prevents infinite recursion; raises `CanonCycleError` with cycle path |

### CWL Integration

| Decision | Choice | Rationale |
|---|---|---|
| Workflow language | CWL v1.2 | Standard, tooled, schematic/execution separation |
| Canon metadata extension | Small Canon annotation on CWL workflow outputs declaring Hippo entity type + identity parameters | Minimal addition to standard CWL; everything else uses native CWL |
| Tool definitions | Standard CWL `CommandLineTool` | No Canon-specific changes needed |
| Execution | Delegated to configured CWL runner (cwltool default; Toil, Nextflow CWL mode as adapters) | Canon never runs commands directly |

### Component Boundaries (Canon vs. Cappella)

| Concern | Owner |
|---|---|
| Which artifacts to request | Cappella |
| Cohort construction (which samples match criteria X) | Cappella |
| Parallelism across multiple artifact requests | Cappella |
| Failure handling across a batch of requests | Cappella |
| "Does this artifact exist?" | Canon |
| "How do I produce this artifact?" | Canon |
| Walking the dependency chain for a single artifact | Canon |
| Running CWL workflows | Canon (via executor adapter) |
| Ingesting outputs into Hippo | Canon |

### Deferred Decisions

| Question | Priority | Notes |
|---|---|---|
| Partial specification / constraint queries | High | MVP requires exact match; constraint predicates (CEL) deferred to v0.2 |
| Aggregate/collect rules (sample sets, gather steps) | High | CountsMatrix use case requires this; deferred to v0.2 — Cappella handles set logic for now |
| Parameter inheritance / flat vs. normalized provenance metadata | Medium | v0.1: flat inherited metadata on each entity; normalization deferred |
| Visual workflow builder (Excalidraw-like CWL editor) | Low | Use existing CWL visual editors (Rabix Composer) for now |
| DRS URI integration | Medium | Canon outputs get `self` URI from Hippo; DRS server deferred to Hippo v0.2 |
| Snakemake/Nextflow native adapter (non-CWL) | Medium | v0.1: CWL only; native adapters as plugins in v0.2 |
| Federation / cross-lab artifact sharing | Low | Hippo DRS + Canon DRS client; deferred to v0.3 |

---

## Open Questions

| Question | Priority | Notes |
|---|---|---|
| OQ1: Canon rules registry format | High | How does Canon map `(entity_type, params)` → CWL workflow file? Single `canon_rules.yaml`? Directory of per-rule YAML files? |
| OQ2: CWL metadata annotation format | High | How exactly does Canon annotate a CWL workflow output to declare its Hippo entity type and identity parameters? Extension field? Sidecar YAML? |
| OQ3: Output ingestion after CWL run | Medium | CWL outputs are `File` objects. Canon needs to ingest them as Hippo entities. What's the mapping from CWL output → Hippo entity fields? |
| OQ4: Work directory management | Low | Where does Canon put CWL work dirs? How are they cleaned up? |
