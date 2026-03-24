# Canon — Design Specification Index

**Codename:** Canon  
**Component:** Semantic Artifact Resolver  
**Version:** 0.1-draft  
**Last updated:** 2026-03-24

---

## Document Map

| File | Section | Status | Notes |
|---|---|---|---|
| `sec1_overview.md` | 1. Overview & Scope | ✅ Draft complete | |
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
| Execution delegation | CWL executor adapters (cwltool default; Toil, Nextflow CWL mode as plugins) | Canon never implements execution; delegates entirely to CWL runners |
| Storage | Stateless — Hippo is the sole persistent store | Consistent with platform adapter pattern |
| Hippo dependency | Required — Canon cannot function without a Hippo instance | Canon reads registry (does this exist?) and writes results (here's what I made) |

### Resolution Model

| Decision | Choice | Rationale |
|---|---|---|
| Resolution strategy | Lazy recursive — resolve one artifact at a time, walk dependencies on demand | Simpler than upfront DAG planning; avoids building plan objects |
| Artifact identity | Entity type + parameter set, where parameters may be scalars or entity references | Maps directly to Hippo entity queries; entity refs enable graph traversal |
| Reuse check | Query Hippo before any execution | Hippo is the authoritative registry of what has been computed |
| Dependency resolution | Canon calls itself recursively for required inputs | Each `requires:` entry in a Canon rule is resolved the same way as the top-level request |
| Cycle detection | Required — Canon must detect circular rule dependencies | Prevents infinite recursion; raises `CanonCycleError` with cycle path |
| Partial specification (v0.1) | Error — all identity parameters must be fully specified | Exact match only for v0.1; ambiguity is always an error, never silently resolved |

### Entity Reference Model ("Everything is an Entity")

| Decision | Choice | Rationale |
|---|---|---|
| Parameter entity promotion | Key parameters that other entities need to reference become Hippo entities, not scalars | Enables graph traversal queries ("all alignments using STAR against GRCh38") |
| Tool / ToolVersion separation | `Tool` (base type, name + category) and `ToolVersion` (extends Tool, adds version string) as distinct Hippo entity types | Hippo single inheritance / polymorphism naturally supports this; enables "all STAR versions" queries |
| Version required | Canon rules MUST specify tool version; error if omitted | Reproducibility requires exact version — "any STAR" is ambiguous and not allowed |
| Hippo polymorphism | `ToolVersion` extends `Tool` using Hippo's `base:` inheritance | `client.query("Tool")` returns both `Tool` and `ToolVersion` entities; subtypes are fully queryable |
| Entity reference syntax in rules | `ref:EntityType{field=value, nested.field=value}` | Dot notation for traversing reference fields; resolved to Hippo UUID before lookup |
| Candidates for entity promotion | `Tool`, `ToolVersion`, `GenomeBuild`, `GeneAnnotation`, `Sample`, `Cohort` | Anything queried across multiple artifacts or needing its own metadata |
| Non-entity parameters | Scalar pipeline params (quality_cutoff, min_length, max_intron_length, etc.) stay as plain values | Entities only when other things need to point to them or query by them |

### Execution Environment and Reproducibility

| Decision | Choice | Rationale |
|---|---|---|
| Environment configuration | Lives in CWL tool definitions (`DockerRequirement`, `SoftwareRequirement`, `EnvVarRequirement`) — not in Canon rules or ToolVersion entities | CWL already handles this; no duplication; site-specific (Docker vs Singularity vs conda vs modules) |
| Reproducibility record | `WorkflowRun` entity in Hippo records: CWL file + hash, runner + version, execution environment type + digest/hash | Complete recipe for reproducing any run; harvested from CWL provenance output |
| ToolVersion entity content | Semantic identity only: tool name, version string, optional bio.tools/Bioconda links | No container/env info; that's site-specific and belongs in WorkflowRun |
| Execution environment types | docker, singularity, conda, module, local — all recorded uniformly as `execution_environment` JSON on WorkflowRun | Flexible blob; whatever CWL runner captured is recorded verbatim |

### CWL Integration

| Decision | Choice | Rationale |
|---|---|---|
| Workflow language | CWL v1.2 | Standard, tooled, schematic/execution separation |
| Canon metadata extension | Sidecar YAML (`.canon.yaml`) alongside CWL workflow file — declares Hippo entity type + identity parameters for each output | Keeps CWL files standard and valid; Canon annotation is separate |
| Tool definitions | Standard CWL `CommandLineTool` with native requirements | No Canon-specific changes to CWL tool files |
| Execution | Delegated to configured CWL runner (cwltool default; Toil, Nextflow CWL mode as plugins) | Canon never runs commands directly |

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
| Running CWL workflows | Canon (via CWL executor adapter) |
| Recording WorkflowRun provenance | Canon |
| Ingesting outputs into Hippo | Canon |

### Deferred Decisions

| Question | Priority | Notes |
|---|---|---|
| Partial specification / constraint queries | High | v0.1 requires full exact spec; CEL-based constraint predicates deferred to v0.2 |
| Aggregate/collect rules (sample sets, gather steps) | High | CountsMatrix use case; deferred to v0.2 — Cappella handles set logic in v0.1 |
| Snakemake/Nextflow native adapter (non-CWL) | Medium | v0.1: CWL only; native adapters as entry-point plugins in v0.2 |
| Visual workflow builder | Low | Use existing CWL editors (Rabix Composer, cwl-viewer) for now |
| DRS URI integration | Medium | Canon outputs get `self` URI from Hippo; DRS server in Hippo v0.2 |
| Federation / cross-lab artifact sharing | Low | Hippo DRS + Canon DRS client; deferred to v0.3 |
| ToolVersion entity pre-population | Medium | Who creates Tool/ToolVersion entities? Canon lazily on first use, or `hippo-reference-bioconda` plugin? |

---

## Open Questions

| Question | Priority | Notes |
|---|---|---|
| OQ1: Canon sidecar format | High | Exact schema of `.canon.yaml` alongside CWL workflow — how are Hippo entity type and identity params declared per output? |
| OQ2: Output ingestion after CWL run | Medium | CWL outputs are `File` objects with checksums. Canon maps them to Hippo entities using sidecar + CWL output values. Full mapping spec needed. |
| OQ3: Work directory lifecycle | Low | Where does Canon put CWL work dirs? Cleanup policy? |
| OQ4: Partial ref resolution ordering | Medium | When multiple Hippo entities match `ref:ToolVersion{tool.name=STAR}` and no version is given — confirm this is always an error in v0.1, never silent disambiguation |
| OQ5: ToolVersion entity schema | Medium | Exact fields for `Tool` and `ToolVersion` Hippo entity types — part of a Canon reference schema package or user-defined? |
