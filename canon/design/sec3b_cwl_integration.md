## 3b. CWL Integration

**Document status:** Draft v0.1  
**Depends on:** sec3_rules_dsl.md, sec2_architecture.md  
**External reference:** https://www.commonwl.org/v1.2/

---

### 3b.1 Overview

Canon uses CWL (Common Workflow Language v1.2) as its workflow description format. CWL
is a standard, executor-agnostic YAML/JSON format for describing computational workflows
as directed acyclic graphs (DAGs). Canon adds a thin annotation layer (the `.canon.yaml`
sidecar) but does not modify or extend the CWL format itself — all CWL files used by
Canon are fully standard and valid CWL.

This section describes the CWL file structures Canon expects, how environment requirements
are declared, and how Canon invokes CWL workflows at execution time.

---

### 3b.2 CWL File Structure

Canon workflows follow standard CWL v1.2 structure. A typical Canon workflow directory:

```
workflows/
  star_align.cwl           # Workflow: orchestrates the alignment DAG
  star_align.canon.yaml    # Canon sidecar: output → Hippo entity mapping
  tools/
    star.cwl               # CommandLineTool: runs STAR aligner
    samtools_sort.cwl      # CommandLineTool: sorts BAM output
    samtools_index.cwl     # CommandLineTool: indexes sorted BAM
```

Canon rules reference the **workflow file** (e.g. `star_align.cwl`), not individual tool
files. Tool files are implementation details of the workflow — Canon has no knowledge of
them.

#### CommandLineTool

A CWL `CommandLineTool` wraps a single command-line step. Tool files are reusable across
multiple workflows and live in a shared `tools/` directory.

```yaml
# tools/star.cwl
cwlVersion: v1.2
class: CommandLineTool

requirements:
  DockerRequirement:
    dockerPull: "quay.io/biocontainers/star:2.7.11a--h9ee0642_0"
  ResourceRequirement:
    coresMin: 8
    ramMin: 32000   # MB

baseCommand: STAR

arguments:
  - --runMode
  - alignReads

inputs:
  fastq:
    type: File
    inputBinding:
      prefix: --readFilesIn
  genome_index:
    type: Directory
    inputBinding:
      prefix: --genomeDir
  sample_id:
    type: string
    inputBinding:
      prefix: --outSAMattrRGline
      valueFrom: "ID:$(inputs.sample_id)"
  output_prefix:
    type: string
    default: "Aligned"
    inputBinding:
      prefix: --outFileNamePrefix

outputs:
  bam:
    type: File
    outputBinding:
      glob: "$(inputs.output_prefix)Aligned.sortedByCoord.out.bam"
  log:
    type: File
    outputBinding:
      glob: "$(inputs.output_prefix)Log.final.out"
```

#### Workflow

A CWL `Workflow` connects tools into a DAG. Each `step` runs a tool and wires its inputs
and outputs to other steps or to the workflow's top-level inputs/outputs.

```yaml
# star_align.cwl
cwlVersion: v1.2
class: Workflow

inputs:
  fastq:      File
  genome_index: Directory
  sample_id:  string
  genome_build: string      # passed through to sidecar, not used by STAR itself
  aligner:    string        # Hippo UUID of ToolVersion entity — passed through
  quality_cutoff: int
  min_length:  int

outputs:
  bam:
    type: File
    outputSource: sort/sorted_bam
  bam_index:
    type: File
    outputSource: index/bam_index

steps:
  align:
    run: tools/star.cwl
    in:
      fastq: fastq
      genome_index: genome_index
      sample_id: sample_id
    out: [bam, log]

  sort:
    run: tools/samtools_sort.cwl
    in:
      bam: align/bam
    out: [sorted_bam]

  index:
    run: tools/samtools_index.cwl
    in:
      bam: sort/sorted_bam
    out: [bam_index]
```

**Passthrough inputs** — `genome_build`, `aligner`, `quality_cutoff`, `min_length` are
declared as workflow inputs even though STAR doesn't use them. They are included so Canon
can pass them through from the rule's `execute.inputs:` and the sidecar can reference them
via `{inputs.genome_build}` etc. when constructing the Hippo entity. This is the standard
pattern for carrying provenance metadata through a CWL workflow.

---

### 3b.3 Environment Requirements

CWL handles execution environment configuration natively. Canon does not add any
environment configuration — it delegates entirely to what the CWL tool files declare.

#### Docker / Singularity

```yaml
requirements:
  DockerRequirement:
    dockerPull: "quay.io/biocontainers/star:2.7.11a--h9ee0642_0"
```

When running with cwltool:
- `cwltool` uses Docker by default if available
- Singularity: `cwltool --singularity star_align.cwl inputs.json`
- No containers: `cwltool --no-container star_align.cwl inputs.json`

The choice of runtime is set in `canon.yaml`, not in the CWL file. The same CWL file
works with any container runtime:

```yaml
# canon.yaml
executor: cwltool
cwltool_options:
  - "--singularity"   # use Singularity instead of Docker
```

#### Conda

CWL's `SoftwareRequirement` is the standard way to declare conda dependencies:

```yaml
requirements:
  SoftwareRequirement:
    packages:
      - package: star
        version: ["2.7.11a"]
        specs:
          - https://anaconda.org/bioconda/star
```

cwltool with conda: `cwltool --beta-conda-dependencies star_align.cwl inputs.json`

#### Environment modules (HPC)

HPC systems using `module load` are typically handled at the Toil adapter level rather
than in CWL files. When using `ToilAdapter` with `--batchSystem slurm`, the Toil job
script can load modules before execution. This is specified in the Toil adapter config:

```yaml
# canon.yaml
executor: toil
toil_options:
  batch_system: slurm
  default_memory: "32G"
  default_cores: 8
  pre_job_script: |
    module load STAR/2.7.11a
    module load samtools/1.17
```

#### No environment (local binaries)

```yaml
# canon.yaml
executor: cwltool
cwltool_options:
  - "--no-container"
```

Assumes all tools are on `$PATH`. Useful for development and testing.

---

### 3b.4 CWL Inputs Format

Canon's `CwltoolAdapter` constructs a CWL `inputs.json` file from the resolved inputs
and passes it to cwltool. The mapping from Canon binding values to CWL input types:

| Canon binding value | CWL input type | inputs.json representation |
|---|---|---|
| Hippo entity URI (`s3://...`, `file://...`) | `File` | `{"class": "File", "location": "<uri>"}` |
| Hippo entity URI for a directory | `Directory` | `{"class": "Directory", "location": "<uri>"}` |
| Scalar string | `string` | `"value"` |
| Scalar integer | `int` | `20` |
| Scalar float | `float` | `0.05` |
| Scalar boolean | `boolean` | `true` |
| Hippo entity UUID (passthrough) | `string` | `"uuid:..."` |

**File staging** — when a Canon binding value is an S3 URI or other remote URI and the
executor is cwltool (which requires local files), Canon's `InputStagingLayer` downloads
the file to `work_dir/staging/` before constructing `inputs.json`. The staged local path
is used in `inputs.json`; the original remote URI is preserved in the Canon binding
context for provenance recording.

File staging is not required for Toil with S3 job store — Toil handles remote URIs natively.
The `CWLExecutorAdapter` declares whether staging is required via `requires_staging: bool`.

---

### 3b.5 CWL Output Parsing

After a successful cwltool run, Canon parses the JSON output object cwltool writes to
stdout. The output object maps CWL output names to file objects:

```json
{
  "bam": {
    "class": "File",
    "location": "file:///work/canon/runs/abc123/Aligned.sortedByCoord.out.bam",
    "basename": "Aligned.sortedByCoord.out.bam",
    "checksum": "sha1:deadbeef...",
    "size": 4521943040
  },
  "bam_index": {
    "class": "File",
    "location": "file:///work/canon/runs/abc123/Aligned.sortedByCoord.out.bam.bai",
    "checksum": "sha1:cafebabe...",
    "size": 2097152
  }
}
```

The `OutputIngestionPipeline` uses this object together with the `.canon.yaml` sidecar
to construct the Hippo entity payload (see sec3 §3.7 and sec6).

**Output relocation** — after parsing, Canon moves (or uploads) output files from the
cwltool work directory to the configured output storage location (local path, S3, etc.)
declared in `canon.yaml`. The final storage URI — not the cwltool work dir path — is
stored as the `uri` field on the Hippo entity.

```yaml
# canon.yaml
output_storage:
  type: local
  base_path: /data/canon-outputs
  # or:
  type: s3
  bucket: lab-data-bucket
  prefix: canon-outputs/
```

---

### 3b.6 CWL Provenance

cwltool supports the W3C PROV standard via `--provenance <dir>`. When enabled, it writes
a full provenance bundle including the CWL document hash, all input/output checksums,
container digests, and timestamps.

Canon captures a subset of this in the `WorkflowRun` entity. If `--provenance` is enabled
in `cwltool_options`, Canon additionally stores the provenance bundle path in the
`WorkflowRun` entity for full audit access:

```yaml
# canon.yaml
executor: cwltool
cwltool_options:
  - "--provenance"
  - ".canon/provenance/{run_id}"
```

This is optional but recommended for maximum reproducibility.

---

### 3b.7 Validation

Canon validates CWL files at startup (as part of rule validation):

```bash
canon rules validate   # validates canon_rules.yaml + CWL files + sidecars
```

Checks performed against CWL files:
- CWL file exists and is valid YAML
- `cwlVersion` is `v1.2` (Canon does not support older CWL versions)
- `class` is `Workflow` (Canon rules must reference workflows, not bare tools)
- All inputs declared in the workflow exist as keys in the rule's `execute.inputs:` block
- All outputs named in the `.canon.yaml` sidecar exist in the workflow's `outputs:` block

Canon does not perform full CWL semantic validation (that is cwltool's job — run
`cwltool --validate star_align.cwl` for full validation).

---

### 3b.8 CWL Compatibility Notes

**CWL version:** Canon requires CWL v1.2. Earlier versions (v1.0, v1.1) are not supported.
CWL v1.2 introduced `networkAccess` and improved `when:` conditional steps; Canon may
rely on these in future versions.

**Subworkflows:** CWL supports nested workflows via `class: Workflow` in a step's `run:`
field. Canon supports this transparently — the outer workflow is what Canon references,
and cwltool handles the nested execution. Canon's sidecar only needs to declare the
outer workflow's outputs.

**Scatter/gather:** CWL v1.2 supports `scatter` on step inputs for parallel array
processing. This is fully supported — the scatter is internal to the CWL workflow and
invisible to Canon. Canon's rule defines one artifact per invocation; scatter/gather
within a workflow is an implementation detail.

**Expression tools:** CWL `ExpressionTool` (JavaScript expressions) is supported but
discouraged. Pure `CommandLineTool` steps are preferred for reproducibility and
portability (some HPC environments restrict JavaScript execution).
