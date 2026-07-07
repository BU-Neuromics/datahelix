# Canon

Semantic dependency resolver and workflow orchestrator for the DataHelix platform.

## Overview

Canon is the semantic resolution layer that sits between the **Hippo** metadata database and concrete workflow executors. Where traditional workflow systems operate on file paths, Canon operates on **metadata specifications** — you declare the kind of entity you want, and Canon figures out whether it already exists or needs to be built.

```
                  ┌─────────────────────────────────────────┐
  canon plan/run  │               Canon                      │
  ─────────────►  │  SemanticPlanner + RulesEngine           │
                  │                                          │
                  │  REUSE ◄── HippoClient ──► Hippo DB      │
                  │  BUILD ──► WorkflowExecutorAdapter        │
                  │             │                            │
                  │        LocalProcess / Container          │
                  └─────────────────────────────────────────┘
```

**REUSE vs BUILD**

When you ask Canon to produce an `AlignmentFile` with `aligner=STAR, genome_build=GRCh38, sample_id=AD-001`, it first queries Hippo for an existing entity matching those metadata fields. If one exists, it is reused with no computation. If not, Canon walks its production rules, recursively resolves dependencies, and builds an execution plan whose tasks are handed off to a workflow executor adapter.

Every BUILD execution records a `WorkflowRun` provenance entity in Hippo, linking input and output entity IDs, timestamps, rule name, and executor type.

**Where Canon fits in DataHelix**

| Component | Role |
|-----------|------|
| Hippo | Structured domain graph (LinkML runtime) — holds all entities and their relationships |
| **Canon** | **Semantic resolver — decides REUSE vs BUILD, orchestrates execution** |
| Cappella | Workflow engine — long-running pipeline scheduling |
| Aperture | Interface layer — REST/GraphQL API surface |
| Bridge | Integration middleware — external system adapters |

---

## Quickstart

### Install

```bash
uv pip install -e .
```

Requires Python ≥ 3.11.

### Write `canon.yaml`

```yaml
# canon.yaml
hippo_url: http://hippo.internal:8000
hippo_token: your-bearer-token          # omit if unauthenticated

executor: local                         # 'local' or 'container'
rules_file: canon_rules.yaml
work_dir: .canon/work

# Required only when executor: container
executor_settings:
  container_image: registry.example.com/bio/workflows:latest
  runtime: docker                       # 'docker' or 'singularity'
```

### Write `canon_rules.yaml`

See [canon_rules.yaml format](#canon_rulesyaml-format) for the full reference. A minimal two-rule file:

```yaml
- name: align-with-star
  produces:
    entity_type: AlignmentFile
    metadata:
      aligner: STAR
      genome_build: "{genome_build}"
      sample_id: "{sample_id}"
  requires:
    - bind: raw_reads
      entity_type: RawReads
      resolve: uri
      metadata:
        sample_id: "{sample_id}"
    - bind: genome_index
      entity_type: GenomeIndex
      resolve: uri
      metadata:
        genome_build: "{genome_build}"
  execute:
    workflow: star_align
    inputs:
      READS: "{raw_reads}"
      GENOME_DIR: "{genome_index}"
      SAMPLE_ID: "{sample_id}"
    outputs:
      - bind: bam
        entity_type: AlignmentFile
        pattern: "{sample_id}.bam"

- name: index-genome
  produces:
    entity_type: GenomeIndex
    metadata:
      genome_build: "{genome_build}"
  requires: []
  execute:
    workflow: star_index
    inputs:
      GENOME_BUILD: "{genome_build}"
    outputs:
      - bind: index
        entity_type: GenomeIndex
        pattern: "{genome_build}_index/"
```

### Run Canon

```bash
# Dry-run: show what would be built or reused
canon plan --entity-type AlignmentFile \
           --metadata aligner=STAR \
           --metadata genome_build=GRCh38 \
           --metadata sample_id=AD-001

# Execute the plan
canon run  --entity-type AlignmentFile \
           --metadata aligner=STAR \
           --metadata genome_build=GRCh38 \
           --metadata sample_id=AD-001

# Check history
canon status
```

---

## `canon_rules.yaml` Format

A rules file is a YAML list of **production rules**. Each rule declares:

- **`produces`** — what entity type and metadata this rule creates
- **`requires`** — which input entities must be resolved first (dependencies)
- **`execute`** — how to invoke the workflow and what outputs to expect

### Full STAR Alignment Example

```yaml
- name: align-with-star
  produces:
    entity_type: AlignmentFile
    metadata:
      aligner: STAR
      genome_build: "{genome_build}"
      sample_id: "{sample_id}"
  requires:
    - bind: raw_reads
      entity_type: RawReads
      resolve: uri
      metadata:
        sample_id: "{sample_id}"
    - bind: genome_index
      entity_type: GenomeIndex
      resolve: uri
      metadata:
        genome_build: "{genome_build}"
  execute:
    workflow: star_align
    inputs:
      READS: "{raw_reads}"
      GENOME_DIR: "{genome_index}"
      SAMPLE_ID: "{sample_id}"
    outputs:
      - bind: bam
        entity_type: AlignmentFile
        pattern: "{sample_id}.bam"
```

### Wildcards

Curly-brace placeholders like `{genome_build}` are **wildcards**. Canon resolves them from two sources, in priority order:

1. **The caller's metadata spec** — values passed via `--metadata` on the CLI
2. **Fields from resolved input entities** — e.g. a `RawReads` entity whose `data` dict contains `sample_id`

If a wildcard cannot be resolved from either source, Canon raises a `CanonPlanningError`.

### `produces` section

```yaml
produces:
  entity_type: AlignmentFile      # The Hippo entity type this rule creates
  metadata:
    aligner: STAR                 # Literal value — no wildcard needed
    genome_build: "{genome_build}" # Wildcard resolved at plan time
    sample_id: "{sample_id}"
```

Canon matches this rule when a caller requests an `AlignmentFile` with `aligner=STAR`. Wildcard fields are filled from the caller's request or dependency entities.

### `requires` section

Each entry describes one input entity that must exist (or be built) before this rule runs:

```yaml
requires:
  - bind: raw_reads           # Name used to reference this entity in 'execute.inputs'
    entity_type: RawReads     # Hippo entity type to query/build
    resolve: uri              # How to extract a value from the entity: uri | field:<name> | inline:<value> | json
    metadata:
      sample_id: "{sample_id}"  # Filter metadata (wildcards allowed)
```

**`resolve` options:**

| Value | Description |
|-------|-------------|
| `uri` | Extract `entity['data']['uri']` (default) |
| `field:<name>` | Extract `entity['data'][<name>]` |
| `inline:<value>` | Always use the literal string `<value>` |
| `json` | JSON-serialize the entire entity dict |

### `execute` section

```yaml
execute:
  workflow: star_align        # Script name (local: scripts/star_align.sh) or container entrypoint
  inputs:
    READS: "{raw_reads}"      # Environment variable → resolved value of the 'raw_reads' binding
    GENOME_DIR: "{genome_index}"
    SAMPLE_ID: "{sample_id}"
  outputs:
    - bind: bam               # Logical name for this output
      entity_type: AlignmentFile  # Hippo entity type to register
      pattern: "{sample_id}.bam"  # Expected output filename pattern
```

Input values in `execute.inputs` use `{bind_name}` placeholders that reference the resolved values from `requires` bindings. Wildcard placeholders (`{sample_id}`) are also valid here.

---

## `canon_outputs.json` Format

Every workflow script must write a `.canon_outputs.json` file to the Canon work directory before it exits. Canon reads this file to register new entities in Hippo.

### Schema

```json
{
  "entities": [
    {
      "entity_type": "AlignmentFile",
      "data": {
        "uri": "file:///data/outputs/AD-001.bam",
        "aligner": "STAR",
        "genome_build": "GRCh38",
        "sample_id": "AD-001",
        "md5": "d41d8cd98f00b204e9800998ecf8427e",
        "size_bytes": 4831838208
      }
    }
  ]
}
```

**Top-level fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entities` | array | yes | List of entities to register in Hippo |

**Per-entity fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entity_type` | string | yes | Hippo entity type (must match a known schema type) |
| `data` | object | yes | Arbitrary key-value metadata for the entity |

`data` fields are schema-defined by Hippo. At minimum, include any fields that downstream rules or consumers will filter on. Canon does not enforce a fixed schema beyond `entity_type` and `data`.

**Shell script example (local executor):**

```bash
#!/usr/bin/env bash
# scripts/star_align.sh
set -euo pipefail

STAR --runThreadN 8 \
     --genomeDir "$GENOME_DIR" \
     --readFilesIn "$READS" \
     --outSAMtype BAM SortedByCoordinate \
     --outFileNamePrefix "${CANON_WORK_DIR}/${SAMPLE_ID}_"

cat > "${CANON_WORK_DIR}/.canon_outputs.json" <<EOF
{
  "entities": [
    {
      "entity_type": "AlignmentFile",
      "data": {
        "uri": "file://${CANON_WORK_DIR}/${SAMPLE_ID}_Aligned.sortedByCoord.out.bam",
        "aligner": "STAR",
        "genome_build": "${GENOME_BUILD}",
        "sample_id": "${SAMPLE_ID}"
      }
    }
  ]
}
EOF
```

The `CANON_WORK_DIR` environment variable is set by Canon to the task's working directory.

---

## Executor Adapters

Canon delegates workflow execution to pluggable **executor adapters**. Two are bundled; additional adapters can be registered via the `canon.executor_adapters` entry point group.

### LocalProcess Adapter

Runs workflows as local subprocesses. The `workflow` field in a rule's `execute` section must resolve to a shell script.

**canon.yaml:**
```yaml
executor: local
work_dir: .canon/work
```

**Conventions:**
- Canon looks for `scripts/<workflow>.sh` (or a path relative to the working directory).
- Each `execute.inputs` key-value pair is passed as an environment variable to the script.
- `CANON_WORK_DIR` is set to the task's isolated work directory.
- The script must write `.canon_outputs.json` to `$CANON_WORK_DIR` before exiting.

### Container Adapter

Runs workflows inside Docker or Singularity containers. The `workflow` field is the entrypoint command executed inside the container.

**canon.yaml:**
```yaml
executor: container
executor_settings:
  container_image: registry.example.com/bio/workflows:latest
  runtime: docker          # or 'singularity'
work_dir: .canon/work
```

**Runtime behaviour:**

| Runtime | Command template |
|---------|-----------------|
| Docker | `docker run --rm -v {work_dir}:/canon_work -e KEY=VALUE ... {image} {workflow}` |
| Singularity | `singularity exec --bind {work_dir}:/canon_work --env KEY=VALUE ... {image} {workflow}` |

The work directory is mounted to `/canon_work` inside the container. Scripts should write `.canon_outputs.json` to `/canon_work/.canon_outputs.json`.

### Plugin Entry Point Group

Third-party adapters (e.g. Nextflow, Snakemake, Cromwell) register under `canon.executor_adapters`:

```toml
# pyproject.toml of the plugin package
[project.entry-points."canon.executor_adapters"]
nextflow = "canon_nextflow:NextflowExecutorAdapter"
```

The adapter class must subclass `canon.executors.base.WorkflowExecutorAdapter` and implement four methods:

```python
from pathlib import Path
from canon.config import CanonConfig
from canon.executors.base import WorkflowExecutorAdapter, ExecutorInputs, RunHandle, RunStatus
from canon.plan import CanonTask


class MyExecutorAdapter(WorkflowExecutorAdapter):

    def __init__(self, config: CanonConfig) -> None:
        super().__init__(config)
        # read from config.executor_settings as needed

    def render(self, task: CanonTask) -> ExecutorInputs:
        """Translate a CanonTask into concrete executor inputs.

        Resolve wildcard placeholders in task.rule.execute.inputs using
        task.wildcard_bindings and task.input_entities.
        Return an ExecutorInputs(workflow_path=..., inputs={...}).
        """

    def submit(self, inputs: ExecutorInputs) -> RunHandle:
        """Submit a workflow for execution.

        Launch the workflow (subprocess, API call, etc.) and return
        an opaque RunHandle(run_id=..., executor_type='my_executor').
        """

    def poll(self, handle: RunHandle) -> RunStatus:
        """Check the status of a submitted run.

        Return one of: RunStatus.PENDING, RUNNING, SUCCEEDED, FAILED.
        """

    def collect_outputs(self, handle: RunHandle) -> Path:
        """Retrieve the work directory path after a SUCCEEDED run.

        Canon will read .canon_outputs.json from the returned path.
        """
```

To use the adapter, set `executor: my_executor` in `canon.yaml` (matching the entry point name).

---

## CLI Reference

All commands accept `--config` to override the default `canon.yaml` path and `--rules` to override `rules_file`.

---

### `canon plan`

Resolve the dependency graph and print the execution plan without running anything.

```
canon plan [OPTIONS]

Options:
  --entity-type TEXT       Target entity type  [required]
  --metadata KEY=VALUE     Metadata filter, repeatable  [required]
  --config PATH            Path to canon.yaml  [default: canon.yaml]
  --rules PATH             Override rules_file from config
```

**Example:**
```bash
canon plan \
  --entity-type AlignmentFile \
  --metadata aligner=STAR \
  --metadata genome_build=GRCh38 \
  --metadata sample_id=AD-001
```

**Output:**
```
Execution plan for AlignmentFile {aligner=STAR, genome_build=GRCh38, sample_id=AD-001}

  [REUSE] GenomeIndex          genome_build=GRCh38          ent-042
  [REUSE] RawReads             sample_id=AD-001             ent-017
  [BUILD] AlignmentFile        align-with-star              sample_id=AD-001, genome_build=GRCh38

1 task(s) to build, 2 entity(s) to reuse.
```

---

### `canon run`

Execute the plan: build any missing entities, ingest outputs into Hippo, and record provenance.

```
canon run [OPTIONS]

Options:
  --entity-type TEXT       Target entity type  [required]
  --metadata KEY=VALUE     Metadata filter, repeatable  [required]
  --config PATH            Path to canon.yaml  [default: canon.yaml]
  --rules PATH             Override rules_file from config
```

**Example:**
```bash
canon run \
  --entity-type AlignmentFile \
  --metadata aligner=STAR \
  --metadata genome_build=GRCh38 \
  --metadata sample_id=AD-001
```

**What happens:**
1. Loads `canon.yaml` and `canon_rules.yaml`.
2. Queries Hippo — entities already present are marked REUSE.
3. Recursively resolves missing entities through production rules.
4. For each BUILD task, submits the workflow to the configured executor, polls until completion, ingests `.canon_outputs.json`, and records a `WorkflowRun` provenance entity.
5. Exits non-zero if any task fails. Run history is persisted to `~/.canon/runs.db`.

---

### `canon status`

Show recent run history from the local SQLite database (`~/.canon/runs.db`).

```
canon status [OPTIONS]

Options:
  --limit INTEGER          Number of recent runs to show  [default: 20]
```

**Example:**
```bash
canon status
```

**Output:**
```
Recent Canon runs

  run_id            rule_name         status     started_at            outputs
  run-a1b2c3        align-with-star   SUCCEEDED  2026-03-20T14:22:01   2
  run-d4e5f6        index-genome      SUCCEEDED  2026-03-20T14:21:58   1
```

---

### `canon rules`

Inspect and validate the rules file.

#### `canon rules list`

Print a table of all loaded rules.

```
canon rules list [OPTIONS]

Options:
  --config PATH    Path to canon.yaml  [default: canon.yaml]
  --rules PATH     Override rules_file from config
```

**Example:**
```bash
canon rules list
```

**Output:**
```
Canon rules  (canon_rules.yaml)

  Name              Produces         Requires
  align-with-star   AlignmentFile    RawReads, GenomeIndex
  index-genome      GenomeIndex      —
  qc-reads          QCReport         —
```

#### `canon rules validate`

Validate the rules file for YAML correctness, schema conformance, and duplicate rule names.

```
canon rules validate [OPTIONS]

Options:
  --config PATH    Path to canon.yaml  [default: canon.yaml]
  --rules PATH     Override rules_file from config
```

**Example:**
```bash
canon rules validate
# ✓ canon_rules.yaml: 3 rules, no errors.

# On failure:
# ✗ Duplicate rule name: 'align-with-star' (rules 1 and 3)
# ✗ Rule 2: 'requires[0].entity_type' is required
```

Exits non-zero if any validation error is found. Suitable for CI pre-flight checks.

---

## Exception Reference

| Exception | Raised when |
|-----------|-------------|
| `CanonValidationError` | Config or rules file is invalid; entity not found in Hippo |
| `CanonPlanningError` | No rule matches the requested entity; wildcard unresolvable |
| `CanonCycleError` | Dependency graph contains a cycle |
| `CanonExecutorError` | Workflow submission or polling fails; HTTP 4xx/5xx from Hippo |
| `CanonIngestionError` | `.canon_outputs.json` is missing, malformed, or fails to ingest |

All exceptions inherit from `CanonError`.
