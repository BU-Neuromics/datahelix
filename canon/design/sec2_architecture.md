## 2. Architecture

**Document status:** Draft v0.1  
**Depends on:** sec1_overview.md

---

### 2.1 Component Overview

Canon is structured as a three-layer pipeline. Each layer has a single responsibility and
a clean interface to the layers around it.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Canon Pipeline                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1. Rules Layer                                               │   │
│  │                                                               │   │
│  │  canon_rules.yaml + *.canon.yaml sidecars                    │   │
│  │  RuleRegistry — maps (entity_type, params) → CWL workflow    │   │
│  │  Rule validation at startup                                   │   │
│  └──────────────────────────┬────────────────────────────────────┘   │
│                             │  matching rule                         │
│  ┌──────────────────────────▼────────────────────────────────────┐   │
│  │  2. Resolver Layer                                             │   │
│  │                                                               │   │
│  │  CanonResolver — the core engine                              │   │
│  │    ├── EntityRefResolver: ref:T{...} → Hippo UUID             │   │
│  │    ├── MosaicQueryClient: does this entity exist?              │   │
│  │    ├── RecursivePlanner: resolve requires[], detect cycles    │   │
│  │    └── Decision: REUSE (found) or BUILD (not found)           │   │
│  └──────────────────────────┬────────────────────────────────────┘   │
│                             │  BUILD: resolved inputs + CWL path     │
│  ┌──────────────────────────▼────────────────────────────────────┐   │
│  │  3. Executor Layer                                             │   │
│  │                                                               │   │
│  │  CWLExecutorAdapter (ABC)                                     │   │
│  │    ├── CwltoolAdapter (bundled — only built-in adapter)                          │   │
│  │    ├── canon-executor-toil, canon-executor-nextflow (plugins)                          │   │
│  │    └── (any canon.executor_adapters entry point)   │   │
│  │                                                               │   │
│  │  OutputIngestionPipeline                                      │   │
│  │    ├── Parse CWL output + .canon.yaml sidecar                 │   │
│  │    ├── Ingest output entity into Hippo                        │   │
│  │    └── Record WorkflowRun provenance entity                   │   │
│  └──────────────────────────┬────────────────────────────────────┘   │
│                             │  Hippo entity UUID + URI               │
└─────────────────────────────┼───────────────────────────────────────-┘
                              │
                    ┌─────────▼──────────┐
                    │       Hippo        │
                    │  (entity registry) │
                    └────────────────────┘
```

Every `canon get` call passes through all three layers. REUSE short-circuits at the
Resolver Layer — no execution, no ingestion. BUILD continues through to the Executor Layer.

---

### 2.2 Layer 1: Rules Layer

The Rules Layer is Canon's knowledge base — it knows how to produce artifacts.

**`canon_rules.yaml`** is the registry of production rules. Each rule declares:
- What it produces: entity type + identity parameters (scalars and entity references)
- What it requires: named input bindings, each resolved by a recursive `canon get`
- How to execute: path to a CWL workflow file + input parameter mappings

```
canon/
  canon_rules.yaml          # rule registry
  workflows/
    star_align.cwl           # CWL workflow
    star_align.canon.yaml    # Canon sidecar: output → Hippo entity mapping
    cutadapt.cwl
    cutadapt.canon.yaml
    htseq_count.cwl
    htseq_count.canon.yaml
```

**Canon sidecar (`.canon.yaml`)** — a small YAML file alongside each CWL workflow
declaring what Hippo entity types the CWL outputs map to and which CWL output values
become which Hippo entity fields:

```yaml
# star_align.canon.yaml
outputs:
  bam:
    entity_type: AlignmentFile
    identity_fields:          # these fields uniquely identify the artifact
      - aligner
      - genome_build
      - sample
    hippo_fields:             # CWL output value → Hippo entity field mappings
      uri: "{outputs.bam.location}"
      aligner: "{inputs.aligner}"
      genome_build: "{inputs.genome_build}"
      sample: "{inputs.sample}"
      read_count: "{outputs.bam.stats.mapped_reads}"  # optional scalar
```

The sidecar keeps CWL files entirely standard and valid — no Canon-specific extensions to
the CWL format itself.

**`RuleRegistry`** loads `canon_rules.yaml` at startup, validates all rules (no duplicate
produces specs, all referenced CWL files exist, all sidecars present), and provides
`find_rule(entity_type, params) → Rule | None`.

---

### 2.3 Layer 2: Resolver Layer

The Resolver Layer is the core of Canon. It is the only layer that understands the
difference between REUSE and BUILD.

**`EntityRefResolver`** resolves entity reference parameters before any Hippo query.
`ref:ToolVersion{tool.name=STAR, version=2.7.11a}` becomes a Hippo UUID by querying
the entity registry. Dot notation traverses reference fields. Exact match required;
multiple matches or zero matches both raise `CanonResolutionError`.

**`MosaicQueryClient`** wraps the Hippo REST API for Canon's two read operations:
- `find_entity(entity_type, params) → Entity | None` — does this artifact exist?
- `get_entity(entity_id) → Entity` — fetch by UUID

**`RecursivePlanner`** is the central algorithm (described in full in sec4):

```
def resolve(entity_type, params) → URI:
    # 1. Resolve all entity references in params to UUIDs
    resolved_params = entity_ref_resolver.resolve(params)

    # 2. Check Hippo: does this artifact already exist?
    entity = hippo.find_entity(entity_type, resolved_params)
    if entity:
        return entity.uri  # REUSE

    # 3. Find a rule that can produce it
    rule = rule_registry.find_rule(entity_type, resolved_params)
    if not rule:
        raise CanonNoRuleError(entity_type, resolved_params)

    # 4. Resolve all required inputs (recursive)
    inputs = {}
    for binding in rule.requires:
        inputs[binding.name] = resolve(binding.entity_type, binding.params)

    # 5. Execute (Layer 3)
    output_uri = executor.run(rule.cwl_workflow, inputs, resolved_params)
    return output_uri
```

**Cycle detection** runs during recursive resolution using a grey-set (in-progress) tracker.
If `resolve(A)` triggers `resolve(B)` which triggers `resolve(A)`, Canon raises
`CanonCycleError` with the full cycle path before any execution begins.

---

### 2.4 Layer 3: Executor Layer

The Executor Layer runs CWL workflows and ingests their outputs. It has no knowledge of
Canon rules or entity references — it receives concrete file paths and parameter values.

**`CWLExecutorAdapter` (ABC)**:

```python
class CWLExecutorAdapter(ABC):
    def run(
        self,
        cwl_path: Path,
        inputs: dict[str, Any],   # concrete values, no entity refs
        work_dir: Path,
    ) -> CWLRunResult:
        """Execute the CWL workflow. Returns output file locations and metadata."""

    def version(self) -> str:
        """CWL runner version string, recorded in WorkflowRun provenance."""
```

Built-in adapters:
- **`CwltoolAdapter`** (bundled): invokes `cwltool <workflow.cwl> <inputs.json>` as a subprocess,
  captures stdout/stderr, parses the JSON output object
- All other adapters (Toil, Nextflow, etc.) are installable plugin packages, not bundled
  (`pip install canon-executor-toil`, `pip install canon-executor-nextflow`, etc.)
- Plugins discovered via entry point group `canon.executor_adapters`

**`OutputIngestionPipeline`** runs after a successful CWL execution:
1. Reads the CWL JSON output (file locations, checksums, any scalar outputs)
2. Reads the `.canon.yaml` sidecar to determine Hippo entity type and field mappings
3. Constructs the Hippo entity payload and POSTs it to `POST /entities`
4. Creates a `WorkflowRun` entity in Hippo recording the full execution provenance

**`WorkflowRun` entity** (recorded for every BUILD execution):

```yaml
entity_type: WorkflowRun
data:
  rule_name: align_reads
  cwl_workflow: "workflows/star_align.cwl"
  cwl_workflow_hash: "sha256:abc123..."
  cwl_runner: cwltool
  cwl_runner_version: "3.1.20240112164112"
  execution_environment:
    type: docker                                    # or singularity, conda, module, local
    image: "quay.io/biocontainers/star:2.7.11a"
    digest: "sha256:def456..."
  inputs:                                           # resolved concrete values
    fastq: "drs://datahelix.lab.org/fastq-uuid"
    genome_index: "s3://bucket/star_index_GRCh38"
  output_entity_id: "alignment-uuid"
  started_at: "2026-03-24T09:00:00Z"
  completed_at: "2026-03-24T09:45:00Z"
  status: completed                                 # completed | failed
  exit_code: 0
```

---

### 2.5 Package Structure

```
canon/
│
├── config.py                  # CanonConfig: load from canon.yaml
├── exceptions.py              # Exception hierarchy
├── types.py                   # Spec, EntityRef, ResolvedInput, WildcardBinding
│
├── rules/
│   ├── models.py              # ProductionRule, InputBinding, ProducesSpec, ExecuteSpec
│   ├── loader.py              # RulesLoader: parse + validate canon_rules.yaml
│   └── registry.py            # RuleRegistry: find_rule(entity_type, params)
│
├── resolver/
│   ├── entity_ref.py          # EntityRefResolver: ref:T{...} → Hippo UUID
│   ├── hippo_client.py        # MosaicQueryClient: find_entity, get_entity, ingest_entity
│   └── planner.py             # RecursivePlanner: resolve(), cycle detection
│
├── executors/
│   ├── base.py                # CWLExecutorAdapter ABC, CWLRunResult
│   └── cwltool.py             # CwltoolAdapter (bundled, only built-in adapter)
│
├── ingestion/
│   ├── sidecar.py             # Parse .canon.yaml sidecar files
│   ├── pipeline.py            # OutputIngestionPipeline: CWL output → Hippo entity
│   └── provenance.py          # WorkflowRun entity construction + POST
│
└── cli/
    ├── main.py                # Typer app entry point
    └── commands/
        ├── get.py             # canon get — resolve one artifact
        ├── plan.py            # canon plan — dry run, show REUSE/BUILD decisions
        ├── rules.py           # canon rules list/validate
        └── status.py          # canon status — recent WorkflowRun entities from Hippo
```

---

### 2.6 Data Flow: REUSE path

```
User: canon get AlignmentFile \
        --param genome_build="ref:GenomeBuild{name=GRCh38}" \
        --param aligner="ref:ToolVersion{tool.name=STAR,version=2.7.11a}" \
        --param sample="ref:Sample{id=AD001}"

1. EntityRefResolver resolves each ref:... to a Hippo UUID
   genome_build → uuid:gbuild-123
   aligner      → uuid:toolv-456
   sample       → uuid:sample-789

2. MosaicQueryClient queries Hippo:
   GET /entities?entity_type=AlignmentFile
     &genome_build=gbuild-123&aligner=toolv-456&sample=sample-789

3. Found: AlignmentFile entity uuid:align-abc
   URI: s3://bucket/alignments/AD001_GRCh38_STAR.bam

4. Return: s3://bucket/alignments/AD001_GRCh38_STAR.bam
   (No execution performed)
```

---

### 2.7 Data Flow: BUILD path

```
User: canon get AlignmentFile \
        --param genome_build="ref:GenomeBuild{name=GRCh38}" \
        --param aligner="ref:ToolVersion{tool.name=STAR,version=2.7.11a}" \
        --param sample="ref:Sample{id=AD002}"    ← new sample, not yet aligned

1. EntityRefResolver resolves refs → UUIDs (as above)

2. MosaicQueryClient queries Hippo → Not found

3. RuleRegistry.find_rule("AlignmentFile", {...}) → align_reads rule

4. RecursivePlanner resolves requires[]:
   a. canon get FastqFile{sample=sample-002}
      → Found in Hippo: s3://bucket/fastq/AD002_R1.fastq.gz  (REUSE)
   b. canon get StarIndex{genome_build=gbuild-123, aligner=toolv-456}
      → Found in Hippo: s3://bucket/indices/GRCh38_STAR_2.7.11a/  (REUSE)

5. CwltoolAdapter.run(
     cwl_path="workflows/star_align.cwl",
     inputs={
       fastq: "s3://bucket/fastq/AD002_R1.fastq.gz",
       genome_index: "s3://bucket/indices/GRCh38_STAR_2.7.11a/",
       genome_build: "GRCh38",
       aligner_version: "2.7.11a",
       sample_id: "AD002"
     },
     work_dir=".canon/work/align-runs/20260324-090000"
   )
   → CWL runs STAR, produces AD002_GRCh38_STAR.bam

6. OutputIngestionPipeline:
   a. Parse star_align.canon.yaml sidecar
   b. POST /entities → AlignmentFile{uri=s3://..., genome_build=gbuild-123, ...}
      → uuid:align-def

7. ProvenanceRecorder:
   POST /entities → WorkflowRun{rule=align_reads, cwl=star_align.cwl,
                                runner=cwltool/3.1, env=docker/sha256:...,
                                output=align-def, status=completed}

8. Return: s3://bucket/alignments/AD002_GRCh38_STAR.bam
```

---

### 2.8 Hippo Entity Types Used by Canon

Canon relies on the following entity types being present in the Hippo deployment.
These are defined in the **Canon Hippo reference schema**, which is bundled inside the
`canon` package and registered as a `hippo.reference_loaders` entry point.

**Installing Canon's schema into a Hippo deployment:**

```bash
pip install canon          # installs canon + bundles the reference schema loader
hippo reference install canon   # writes Tool, ToolVersion, etc. into Hippo's schema + migrates
```

`hippo reference install canon` only needs to be run once per Hippo deployment (or after
upgrading Canon to a new version). Canon raises `CanonConfigError` at startup if these
types are not found in the Hippo instance it is configured to use.

The Canon package and its Hippo reference schema are versioned and released together.
Schema changes always require a new Canon release — there is no independent schema version.

| Entity Type | Base Type | Purpose |
|---|---|---|
| `Tool` | — | Software tool identity (name, category, bio.tools ID) |
| `ToolVersion` | `Tool` | Specific version of a tool. Required in all Canon rules. |
| `GenomeBuild` | — | Reference genome assembly (name, patch, species, UCSC/NCBI accession) |
| `GeneAnnotation` | — | Gene annotation release (source, version, genome build ref) |
| `WorkflowRun` | — | Canon execution provenance record |

All domain entity types (`AlignmentFile`, `FastqFile`, `StarIndex`, `CountsMatrix`, etc.)
are deployment-specific and defined in the user's Hippo schema configuration — not by Canon.

Hippo's single-inheritance polymorphism means `client.query("Tool")` returns both `Tool`
and `ToolVersion` entities. Canon always queries `ToolVersion` directly — exact version
matching is always required.

See `sec6_mosaic_integration.md` for the full field-level schema of each Canon entity type.

---

### 2.9 Configuration

Canon is configured via `canon.yaml` in the project directory:

```yaml
# Minimum required configuration
mosaic_url: "http://127.0.0.1:8000"
mosaic_token: "dev-token"
executor: cwltool
rules_file: canon_rules.yaml

# Optional
work_dir: .canon/work
cwltool_options:
  - "--no-container"     # for local runs without Docker
```

`executor` selects the CWL runner adapter. `cwltool` is the default and is bundled with Canon — no additional install needed. Additional adapters
are installed as Python packages and discovered via the `canon.executor_adapters` entry
point group.

See `reference_canon_yaml.md` for the complete configuration schema.
