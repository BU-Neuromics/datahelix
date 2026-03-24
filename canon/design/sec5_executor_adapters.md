## 5. Executor Adapters

**Document status:** Draft v0.1  
**Depends on:** sec2_architecture.md, sec3b_cwl_integration.md

---

### 5.1 Overview

Canon delegates all CWL workflow execution to a `CWLExecutorAdapter`. The adapter
abstracts the differences between local execution (cwltool), HPC/cloud execution (Toil),
and future backends, presenting a uniform interface to the resolution algorithm.

Canon ships one built-in adapter — `CwltoolAdapter` — as part of the core package.
Additional adapters are installed as Python packages and discovered via the
`canon.executor_adapters` entry point group.

---

### 5.2 CWLExecutorAdapter ABC

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CWLRunResult:
    """Result of a CWL workflow execution."""
    outputs: dict[str, Any]      # CWL output object (file locations, scalars, etc.)
    runner_name: str             # e.g. "cwltool"
    runner_version: str          # e.g. "3.1.20240112164112"
    execution_environment: dict  # {"type": "docker", "image": "...", "digest": "..."}
    work_dir: Path               # where CWL wrote its outputs
    stdout: str                  # captured stdout for debugging
    stderr: str                  # captured stderr for debugging
    exit_code: int


class CWLExecutorAdapter(ABC):
    """Abstract base class for CWL workflow execution backends."""

    name: str           # adapter identifier, matches canon.yaml executor value
    requires_staging: bool = True  # whether remote URIs must be staged to local paths

    @abstractmethod
    def run(
        self,
        cwl_path: Path,
        inputs: dict[str, Any],
        work_dir: Path,
    ) -> CWLRunResult:
        """
        Execute a CWL workflow.

        Args:
            cwl_path: Absolute path to the .cwl workflow file.
            inputs: Resolved inputs dict (all entity refs replaced with concrete values;
                    File objects as {"class": "File", "location": "..."}).
            work_dir: Directory for CWL to write outputs and intermediate files.

        Returns:
            CWLRunResult with output locations and execution metadata.

        Raises:
            CanonExecutorError: if the workflow fails or the runner is unavailable.
        """

    @abstractmethod
    def version(self) -> str:
        """Return the CWL runner version string."""

    def validate_available(self) -> None:
        """
        Check that the underlying runner is installed and accessible.
        Called at Canon startup. Raises CanonConfigError if not available.
        """
        pass
```

---

### 5.3 CwltoolAdapter (built-in, v0.1)

The default adapter. Invokes `cwltool` as a subprocess.

**Requirements:** `cwltool>=3.1` (bundled as a Canon dependency).

**Configuration in `canon.yaml`:**

```yaml
executor: cwltool
cwltool_options:             # optional — passed directly to cwltool CLI
  - "--no-container"         # run without Docker (use PATH binaries)
  # - "--singularity"        # use Singularity instead of Docker
  # - "--provenance"         # write W3C PROV provenance bundle
  # - "--provenance-dir"
  # - ".canon/provenance/{run_id}"
  # - "--parallel"           # run workflow steps in parallel where possible
  # - "--debug"              # verbose cwltool logging
```

**Execution flow:**

```
1. Write inputs dict to {work_dir}/inputs.json
2. subprocess: cwltool [--options] {cwl_path} {work_dir}/inputs.json
   stdout → JSON output object
   stderr → cwltool logs
3. Parse stdout JSON → CWLRunResult.outputs
4. Detect execution environment from cwltool's provenance output or Docker API
5. Return CWLRunResult
```

**Environment detection:**

After execution, `CwltoolAdapter` inspects which container runtime was used and captures
the image digest for `WorkflowRun.execution_environment`:

- Docker available + `DockerRequirement` in CWL → `type: docker`, image + digest from `docker inspect`
- Singularity flag set → `type: singularity`, image path + hash
- `--no-container` flag → `type: local`, records `$PATH` state
- `SoftwareRequirement` with conda → `type: conda`, env hash

**File URI handling:**

cwltool writes output files to `work_dir` with `file://` URIs. The `OutputIngestionPipeline`
relocates files to the configured `output_storage` location (local or S3) and rewrites
the URI before storing it in Hippo (see sec6 §6.3).

---

### 5.4 Input Staging Layer

When `adapter.requires_staging = True` (default for `CwltoolAdapter`), Canon stages
remote input files to the local filesystem before constructing `inputs.json`.

**Staging logic:**

```python
def stage_inputs(inputs: dict, work_dir: Path) -> dict:
    """Stage remote URIs to local paths for executors that require local files."""
    staging_dir = work_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    staged = {}

    for key, value in inputs.items():
        if isinstance(value, dict) and value.get("class") in ("File", "Directory"):
            location = value["location"]
            if location.startswith("s3://"):
                local_path = stage_from_s3(location, staging_dir)
                staged[key] = {**value, "location": f"file://{local_path}"}
            elif location.startswith("drs://"):
                access_url = resolve_drs_access_url(location)
                local_path = stage_from_url(access_url, staging_dir)
                staged[key] = {**value, "location": f"file://{local_path}"}
            else:
                staged[key] = value  # already local
        else:
            staged[key] = value  # scalar — no staging needed

    return staged
```

Staged files are cached by URI + checksum within a Canon run session. If the same input
is required by multiple rules in the dependency chain, it is only downloaded once.

Adapters that handle remote URIs natively (e.g. `ToilAdapter` with S3 job store) set
`requires_staging = False` to skip this layer.

---

### 5.5 ToilAdapter (plugin, v0.2)

The Toil adapter is **not bundled with Canon**. It is a separate installable package.
Submits CWL workflows to Toil for execution on HPC clusters or cloud.

**Install:**
```bash
pip install canon-executor-toil    # installs Toil + registers canon.executor_adapters entry point
```

**Configuration:**
```yaml
executor: toil
toil_options:
  batch_system: slurm              # slurm | lsf | kubernetes | aws_batch | local
  default_cores: 8
  default_memory: "32G"
  default_disk: "100G"
  job_store: "file:./toil-jobstore"
  # or:
  job_store: "aws:us-east-1:my-toil-bucket"
  workdir: /scratch/toil-work
  log_level: INFO
  pre_job_script: |               # optional: run before each job (module loads, etc.)
    module load STAR/2.7.11a
```

`ToilAdapter` sets `requires_staging = False` when `job_store` is an S3 URI — Toil
handles S3 file staging natively.

---

### 5.6 Plugin Adapters

Community or institutional adapters are installed as Python packages and discovered via
the `canon.executor_adapters` entry point group:

```toml
# In the adapter package's pyproject.toml:
[project.entry-points."canon.executor_adapters"]
nextflow = "canon_executor_nextflow:NextflowCWLAdapter"
```

Canon discovers all registered adapters at startup. The `executor:` value in `canon.yaml`
selects which one to use.

**Adapter discovery:**
```python
import importlib.metadata

def discover_adapters() -> dict[str, type[CWLExecutorAdapter]]:
    adapters = {}
    for ep in importlib.metadata.entry_points(group="canon.executor_adapters"):
        adapters[ep.name] = ep.load()
    return adapters
```

**Writing a custom adapter:**

1. Subclass `CWLExecutorAdapter`
2. Implement `run()`, `version()`, and optionally `validate_available()`
3. Register via entry point
4. Publish to PyPI as `canon-executor-<name>` or install from git

The adapter receives a fully-resolved `inputs` dict with all entity refs replaced by
concrete values and all file objects in CWL `{"class": "File", "location": "..."}` format.
The adapter is responsible for making those files accessible to its execution backend.

---

### 5.7 Adapter Selection and Validation

At Canon startup, `CanonConfig.validate()`:
1. Discovers all registered adapters
2. Checks that `canon.yaml`'s `executor:` value matches a discovered adapter name
3. Calls `adapter.validate_available()` — verifies the runner binary is on PATH, credentials
   are valid, etc.
4. Raises `CanonConfigError` with a clear message if the selected adapter is unavailable

```
CanonConfigError: Executor 'toil' is configured but not installed.
Install with: pip install canon-executor-toil
```
