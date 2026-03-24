## 6. Hippo Integration

**Document status:** Draft v0.1  
**Depends on:** sec2_architecture.md, sec3_rules_dsl.md, sec4_resolution_algorithm.md

---

### 6.1 Overview

Canon interacts with Hippo in three ways:

1. **Read** — query the entity registry (does this artifact exist?)
2. **Write** — ingest produced artifacts as Hippo entities
3. **Provenance** — record `WorkflowRun` entities for every BUILD execution

All Hippo interaction is via the REST API using the configured `hippo_url` and
`hippo_token`. Canon does not use the Hippo Python SDK directly — it calls the API over
HTTP so that Canon can work against any Hippo deployment (local or remote).

---

### 6.2 HippoQueryClient

Canon's thin HTTP client for Hippo. Uses `httpx` for async-capable requests.

**Methods used by Canon:**

```python
class HippoQueryClient:

    def find_entity(
        self,
        entity_type: str,
        filters: dict[str, Any]
    ) -> Entity | None:
        """
        Query Hippo for one entity matching all filters exactly.
        Returns None if no match. Raises CanonResolutionError if multiple match.
        GET /entities?entity_type=X&field=val&...
        """

    def find_entities(
        self,
        entity_type: str,
        filters: dict[str, Any]
    ) -> list[Entity]:
        """
        Query Hippo for all entities matching filters.
        Used by EntityRefResolver for ref: expressions (must return exactly 1).
        GET /entities?entity_type=X&field=val&...&limit=10
        """

    def get_entity(self, entity_id: str) -> Entity:
        """
        Fetch a single entity by UUID.
        GET /entities/{entity_id}
        """

    def ingest_entity(
        self,
        entity_type: str,
        data: dict[str, Any]
    ) -> Entity:
        """
        Create a new entity in Hippo.
        POST /ingest  body: {"entity_type": X, "data": {...}}
        Returns the created entity with its assigned UUID.
        """

    def find_workflow_run(
        self,
        entity_type: str,
        params: dict,
        status: str
    ) -> Entity | None:
        """
        Check for an in-progress or failed WorkflowRun for this artifact spec.
        Used to prevent duplicate execution.
        """
```

**Query filter encoding:**

Hippo entity reference fields (stored as UUIDs) are queried by UUID value directly.
Scalar fields are queried by exact string match. All filter values are passed as query
parameters to `GET /entities`.

---

### 6.3 Output Ingestion Pipeline

After a successful CWL execution, `OutputIngestionPipeline` ingests the produced artifacts
into Hippo.

**Steps:**

```
1. Parse CWL output JSON (cwltool stdout)
2. Load .canon.yaml sidecar for the executed workflow
3. For each output declared in the sidecar:
   a. Evaluate hippo_fields expressions against CWL output + rule inputs
   b. Relocate output file to configured output_storage (if needed)
   c. POST /ingest → create Hippo entity
   d. Record returned UUID for WorkflowRun linkage
4. Create WorkflowRun entity (§6.4)
```

**Output file relocation:**

cwltool writes output files to the CWL work directory with `file://` URIs. Before
ingesting into Hippo, Canon relocates files to the configured `output_storage`:

```yaml
# canon.yaml
output_storage:
  type: local
  base_path: /data/outputs/{entity_type}/{date}/{run_id}

  # or:
  type: s3
  bucket: lab-data
  prefix: outputs/{entity_type}/{date}/{run_id}/
```

The relocated URI is what gets stored as the `uri` field on the Hippo entity. The CWL
work directory is retained for `--keep-workdir` runs; otherwise it is cleaned up after
successful ingestion.

**Entity field assembly:**

The sidecar's `hippo_fields:` expressions are evaluated to produce the entity data dict:

```python
def evaluate_hippo_fields(
    sidecar_output: SidecarOutput,
    cwl_outputs: dict,        # parsed CWL output JSON
    cwl_inputs: dict,         # inputs passed to CWL
    run_id: str
) -> dict:
    result = {}
    for field_name, expr in sidecar_output.hippo_fields.items():
        result[field_name] = evaluate_expr(expr, cwl_outputs, cwl_inputs, run_id)
    return result
```

Expression evaluation supports:
- `{outputs.<name>.location}` → file URI after relocation
- `{outputs.<name>.checksum}` → SHA1 checksum from CWL output object
- `{outputs.<name>.size}` → file size in bytes
- `{inputs.<name>}` → value from CWL inputs (Hippo UUID for entity ref fields)
- Literal string/numeric values

---

### 6.4 WorkflowRun Entity

Canon creates a `WorkflowRun` entity in Hippo for every BUILD execution. This entity
serves as the complete provenance record for the produced artifact.

**Schema:**

```yaml
entity_type: WorkflowRun
fields:
  # Execution identity
  rule_name:           string, required
  cwl_workflow:        string, required      # relative path to .cwl file
  cwl_workflow_hash:   string                # SHA256 of the CWL file at execution time

  # Runner provenance
  cwl_runner:          string, required      # e.g. "cwltool"
  cwl_runner_version:  string, required      # e.g. "3.1.20240112164112"
  execution_environment: dict, required      # see §6.4.1

  # Inputs (Hippo UUIDs of all resolved input entities)
  input_entities:      list[string]          # list of Hippo UUIDs

  # Output entity
  output_entity_id:    string               # Hippo UUID of the produced artifact

  # Timing and status
  started_at:          datetime, required
  completed_at:        datetime
  status:              enum[running, completed, failed], required
  exit_code:           integer
  error_message:       string               # populated on failure
```

#### 6.4.1 execution_environment

The `execution_environment` field is a JSON object whose structure depends on the
runtime used. Canon records whatever the CWL runner captured.

**Docker:**
```json
{
  "type": "docker",
  "image": "quay.io/biocontainers/star:2.7.11a--h9ee0642_0",
  "digest": "sha256:abc123..."
}
```

**Singularity:**
```json
{
  "type": "singularity",
  "image_path": "/refs/containers/star_2.7.11a.sif",
  "image_hash": "sha256:def456..."
}
```

**Conda:**
```json
{
  "type": "conda",
  "env_name": "star-2.7.11a",
  "env_hash": "sha256:789abc...",
  "env_yaml": "envs/star-2.7.11a.yaml"
}
```

**Local (no container):**
```json
{
  "type": "local",
  "tool_path": "/usr/bin/STAR",
  "tool_version": "2.7.11a"
}
```

#### 6.4.2 WorkflowRun lifecycle

```
canon_get() called
    │
    ├── POST /ingest WorkflowRun{status=running, started_at=now}
    │   → uuid:run-xyz
    │
    ├── [CWL execution]
    │
    ├─── success:
    │       POST /ingest AlignmentFile{...}  → uuid:align-abc
    │       PUT /entities/run-xyz {status=completed, completed_at=now,
    │                              output_entity_id=align-abc, exit_code=0}
    │       return AlignmentFile.uri
    │
    └─── failure:
            PUT /entities/run-xyz {status=failed, completed_at=now,
                                   error_message="...", exit_code=1}
            raise CanonExecutorError(...)
```

---

### 6.5 Canon Reference Schema

The Canon Hippo reference schema defines the entity types that Canon relies on.
It is bundled in the `canon` package and applied via `hippo reference install canon`.

#### Tool

```yaml
entity_type: Tool
fields:
  name:           string, required, indexed    # e.g. "STAR", "cutadapt"
  category:       enum, required               # aligner | trimmer | counter |
                                               # indexer | caller | quantifier | other
  description:    string
  homepage_url:   uri
  biotools_id:    string, indexed              # bio.tools registry ID
  bioconda_name:  string, indexed              # Bioconda package name
```

#### ToolVersion

Extends `Tool` via Hippo's `base:` inheritance.

```yaml
entity_type: ToolVersion
base: Tool
fields:
  version:        string, required, indexed    # semver or date string
  release_date:   date
  bioconda_build: string                       # full Bioconda build string
  changelog_url:  uri
```

`client.query("Tool")` returns both `Tool` and `ToolVersion` entities (Hippo polymorphism).
`client.query("ToolVersion")` returns only `ToolVersion` entities. Canon always uses
`ToolVersion` for resolution — `Tool` alone is never a valid Canon rule parameter.

#### GenomeBuild

```yaml
entity_type: GenomeBuild
fields:
  name:           string, required, indexed    # e.g. "GRCh38", "GRCm39"
  patch:          string, indexed              # e.g. "p14"
  species:        string, required, indexed    # e.g. "Homo sapiens"
  ucsc_name:      string, indexed              # e.g. "hg38"
  ncbi_accession: string, indexed              # e.g. "GCA_000001405.15"
  release_date:   date
  fasta_uri:      uri                          # canonical FASTA location
  fai_uri:        uri                          # FASTA index
```

#### GeneAnnotation

```yaml
entity_type: GeneAnnotation
fields:
  source:         enum, required, indexed      # GENCODE | Ensembl | RefSeq | custom
  version:        string, required, indexed    # e.g. "43" (GENCODE), "111" (Ensembl)
  genome_build:   ref:GenomeBuild, required, indexed
  release_date:   date
  gtf_uri:        uri                          # canonical GTF location
  gff3_uri:       uri
  gene_count:     integer
```

#### WorkflowRun

Defined in §6.4 above.

---

### 6.6 Hippo Configuration Requirements

Canon requires the following Hippo configuration to function correctly:

**Authentication:** Canon uses bearer token authentication. The token is configured in
`canon.yaml` as `hippo_token`. The token must have read+write access to all entity types
used by Canon rules.

**Hippo version:** Canon requires Hippo v0.1.0 or later. The `HippoQueryClient` checks
the Hippo version at startup via `GET /health` and raises `CanonConfigError` if the
version is incompatible.

**Schema:** The Canon reference schema must be applied before use:
```bash
hippo reference install canon
```

Canon validates at startup that `Tool`, `ToolVersion`, `GenomeBuild`, `GeneAnnotation`,
and `WorkflowRun` entity types are present in the Hippo schema. Missing types raise
`CanonConfigError` with instructions to run `hippo reference install canon`.
