# Canon Configuration Reference: `canon.yaml`

**Document status:** Draft v0.1
**Depends on:** sec2_architecture.md, sec5_executor_adapters.md, sec6_mosaic_integration.md

---

## Overview

`canon.yaml` is Canon's project-level configuration file. It lives in the working directory from which `canon` commands are run and is loaded at startup before any operation.

Canon raises `CanonConfigError` at startup if the file is missing, unparseable, or contains invalid values. All validation errors are reported together before any resolution or execution begins.

**Minimum viable configuration:**

```yaml
mosaic_url: "http://127.0.0.1:8000"
mosaic_token: "${MOSAIC_TOKEN}"
executor: cwltool
output_storage:
  type: local
  base_path: /data/canon-outputs
```

**Security note:** `canon.yaml` may be committed to version control provided `mosaic_token` uses environment variable substitution (see below). Never commit a literal token value.

---

## Field Reference

### `mosaic_url`

| Property | Value |
|---|---|
| **Type** | `string` (URI) |
| **Required** | Yes |
| **Default** | — |

URL of the Mosaic instance that Canon reads artifact metadata from and writes results to. Must be reachable from the machine running Canon.

**Examples:**

```yaml
mosaic_url: "http://127.0.0.1:8000"           # local development
mosaic_url: "https://mosaic.lab.example.org"   # remote deployment
mosaic_url: "http://mosaic-service:8000"        # Kubernetes service
```

**Validation:**
- Must be a valid HTTP or HTTPS URI
- Schema (`http://` or `https://`) is required — bare hostnames are rejected
- Canon tests connectivity to `{mosaic_url}/health` at startup; raises `CanonConfigError` if unreachable or if the Mosaic version is incompatible

---

### `mosaic_token`

| Property | Value |
|---|---|
| **Type** | `string` |
| **Required** | Yes |
| **Default** | — |

Bearer token for authenticating to the Mosaic REST API. The token must have read and write access to all entity types used by Canon rules (including `Tool`, `ToolVersion`, `GenomeBuild`, `GeneAnnotation`, `WorkflowRun`, and all domain entity types declared in rules).

**Environment variable substitution** — any value matching `${VAR_NAME}` is replaced with the value of that environment variable at load time:

```yaml
mosaic_token: "${MOSAIC_TOKEN}"         # recommended — token stays out of the file
mosaic_token: "dev-token-abc123"       # literal — safe only for local dev instances
```

If a `${VAR_NAME}` expression is used and the environment variable is not set, Canon raises `CanonConfigError: environment variable MOSAIC_TOKEN is not set`.

**Validation:**
- Must be a non-empty string after environment variable substitution
- Canon does not validate token format — an invalid token produces a `401 Unauthorized` from Mosaic at first use, which Canon surfaces as `CanonConfigError`

---

### `executor`

| Property | Value |
|---|---|
| **Type** | `string` |
| **Required** | Yes |
| **Default** | — |

The CWL executor adapter to use for running workflows. The value must match the `name` attribute of a discovered `CWLExecutorAdapter`.

**Built-in adapter (bundled with Canon):**

| Value | Adapter | Notes |
|---|---|---|
| `cwltool` | `CwltoolAdapter` | Local execution via `cwltool` subprocess. No extra install needed. |

**Plugin adapters (separate install required):**

| Value | Install | Notes |
|---|---|---|
| `toil` | `pip install canon-executor-toil` | HPC/cloud via Toil (Slurm, LSF, Kubernetes, AWS Batch) |
| `nextflow` | `pip install canon-executor-nextflow` | Nextflow CWL mode |

Additional adapters may be installed from git or PyPI; they register themselves via the `canon.executor_adapters` entry point group and are automatically discovered at startup.

**Examples:**

```yaml
executor: cwltool        # local development, Docker or Singularity
executor: toil           # HPC submission (requires canon-executor-toil)
```

**Validation:**
- Must match a discovered adapter name (built-in or via entry point)
- If the executor value is not recognized, Canon lists available adapters and raises `CanonConfigError`
- After selecting an adapter, Canon calls `adapter.validate_available()` — if the underlying runner binary is missing or inaccessible, raises `CanonConfigError` with install instructions

---

### `rules_file`

| Property | Value |
|---|---|
| **Type** | `string` (relative or absolute path) |
| **Required** | No |
| **Default** | `canon_rules.yaml` |

Path to the Canon rules registry file. Relative paths are resolved relative to `canon.yaml`'s directory (the working directory).

```yaml
rules_file: canon_rules.yaml          # default
rules_file: config/my_rules.yaml      # custom location
rules_file: /abs/path/rules.yaml      # absolute path
```

**Validation:**
- File must exist and be valid YAML
- If the file does not exist, Canon raises `CanonConfigError: rules file not found: <path>`

---

### `work_dir`

| Property | Value |
|---|---|
| **Type** | `string` (relative or absolute path) |
| **Required** | No |
| **Default** | `.canon/work` |

Directory where Canon writes CWL work directories, staged input files, and intermediate outputs. Each CWL execution gets its own timestamped subdirectory under `work_dir`.

```yaml
work_dir: .canon/work                     # default — inside project directory
work_dir: /scratch/canon-work             # HPC scratch filesystem
work_dir: /tmp/canon                      # temporary — cleaned by OS on reboot
```

**Directory structure created at runtime:**

```
work_dir/
  staging/                  # staged remote input files (S3, DRS)
  runs/
    align_reads-20260324T090000/
      inputs.json           # CWL inputs written before execution
      <cwltool outputs>     # CWL writes output files here
```

Canon creates `work_dir` and subdirectories automatically. Parent directories must exist.

**Cleanup:** by default, work directories for successful runs are removed after output files are relocated to `output_storage`. Work directories for failed runs are retained for debugging. This behavior can be overridden with `cwltool_options: ["--leave-tmpdir"]`.

**Validation:**
- Parent directory of `work_dir` must exist (Canon creates `work_dir` itself but not its parents)
- Must be writable by the user running Canon

---

### `output_storage`

| Property | Value |
|---|---|
| **Type** | `mapping` |
| **Required** | Yes |
| **Default** | — |

Configures where Canon stores output files produced by CWL workflows. After a workflow completes, Canon moves output files from the CWL work directory to this storage location before ingesting the final URI into Mosaic.

The `output_storage` mapping must contain a `type` field. Additional fields depend on the type.

#### `output_storage.type: local`

Stores outputs on the local filesystem.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"local"` | Yes | Storage backend type |
| `base_path` | `string` | Yes | Root directory for all Canon outputs |

```yaml
output_storage:
  type: local
  base_path: /data/canon-outputs
```

Output files are stored at `{base_path}/{entity_type}/{date}/{run_id}/{filename}`. Example: `/data/canon-outputs/AlignmentFile/2026-03-24/align_reads-abc123/AD002.bam`.

**Validation:** `base_path` must exist and be writable.

#### `output_storage.type: s3`

Stores outputs in an Amazon S3 bucket (or S3-compatible storage).

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"s3"` | Yes | Storage backend type |
| `bucket` | `string` | Yes | S3 bucket name |
| `prefix` | `string` | No | Key prefix for all outputs. Default: `canon-outputs/` |
| `region` | `string` | No | AWS region. If omitted, uses `AWS_DEFAULT_REGION` or SDK default |

```yaml
output_storage:
  type: s3
  bucket: lab-data-bucket
  prefix: canon-outputs/
  region: us-east-1
```

Output files are stored at `s3://{bucket}/{prefix}{entity_type}/{date}/{run_id}/{filename}`. The `s3://` URI is what gets stored on the Mosaic entity.

**Authentication:** uses standard AWS credential chain (`~/.aws/credentials`, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` environment variables, or IAM role). Canon does not accept explicit credentials in `canon.yaml`.

**Validation:** Canon verifies `s3://{bucket}/{prefix}` is writable at startup by attempting a small probe write. Raises `CanonConfigError` if the bucket is inaccessible or permissions are insufficient.

---

### `cwltool_options`

| Property | Value |
|---|---|
| **Type** | `list[string]` |
| **Required** | No |
| **Default** | `[]` |
| **Used when** | `executor: cwltool` only |

A list of additional command-line flags passed verbatim to `cwltool` on every invocation. If `executor` is not `cwltool`, this field is silently ignored.

```yaml
cwltool_options:
  - "--no-container"        # run with local PATH binaries, no Docker
```

```yaml
cwltool_options:
  - "--singularity"         # use Singularity instead of Docker
```

```yaml
cwltool_options:
  - "--parallel"            # run workflow steps in parallel where possible
  - "--provenance"
  - ".canon/provenance/{run_id}"   # write W3C PROV bundle
```

```yaml
cwltool_options:
  - "--debug"               # verbose cwltool logging (useful for troubleshooting)
```

```yaml
cwltool_options:
  - "--disable-ext"         # disallow ExpressionTool (JavaScript) — security hardening
```

**Common combinations:**

| Use case | Options |
|---|---|
| Local dev (no Docker) | `["--no-container"]` |
| HPC with Singularity | `["--singularity"]` |
| Max reproducibility | `["--provenance", ".canon/provenance/{run_id}"]` |
| Debug a failing job | `["--debug", "--leave-tmpdir"]` |
| Security-conscious | `["--disable-ext"]` |

**Validation:**
- Must be a YAML list of strings (not a single string)
- Canon does not validate individual flag values — unknown flags are passed to cwltool and will produce a cwltool error at runtime

---

### `log_level`

| Property | Value |
|---|---|
| **Type** | `string` |
| **Required** | No |
| **Default** | `INFO` |

Controls the verbosity of Canon's own log output to stderr. Does not affect cwltool's logging (use `cwltool_options: ["--debug"]` for that).

| Value | What is logged |
|---|---|
| `DEBUG` | Everything: Mosaic queries + response times, entity ref resolutions, wildcard bindings, rule matching decisions, all HTTP requests |
| `INFO` | Normal operations: REUSE/BUILD decisions, CWL execution start/end, ingestion confirmations, startup summary |
| `WARNING` | Non-fatal anomalies: retry attempts, deprecated config fields, missing optional outputs |
| `ERROR` | Fatal errors only (these also raise exceptions and abort the operation) |

```yaml
log_level: INFO      # default — shows what's happening without being noisy
log_level: DEBUG     # full trace — useful when diagnosing resolution failures
log_level: WARNING   # quiet — good for scripted/batch use via Cappella
```

**Validation:**
- Must be one of `DEBUG`, `INFO`, `WARNING`, `ERROR` (case-insensitive)
- Invalid values raise `CanonConfigError`

---

## Complete Example

Minimal local development configuration:

```yaml
# canon.yaml — local development

mosaic_url: "http://127.0.0.1:8000"
mosaic_token: "${MOSAIC_TOKEN}"
executor: cwltool
rules_file: canon_rules.yaml

output_storage:
  type: local
  base_path: /data/canon-outputs

cwltool_options:
  - "--no-container"

log_level: INFO
```

HPC production configuration (Singularity + S3):

```yaml
# canon.yaml — HPC cluster with Singularity and S3 storage

mosaic_url: "https://mosaic.lab.example.org"
mosaic_token: "${MOSAIC_TOKEN}"
executor: cwltool
rules_file: canon_rules.yaml

work_dir: /scratch/$USER/canon-work

output_storage:
  type: s3
  bucket: lab-genomics-data
  prefix: canon-outputs/
  region: us-east-1

cwltool_options:
  - "--singularity"
  - "--parallel"
  - "--provenance"
  - "/scratch/$USER/canon-provenance/{run_id}"

log_level: INFO
```

Toil/Slurm configuration (plugin adapter):

```yaml
# canon.yaml — Slurm cluster via Toil

mosaic_url: "https://mosaic.lab.example.org"
mosaic_token: "${MOSAIC_TOKEN}"
executor: toil

output_storage:
  type: s3
  bucket: lab-genomics-data
  prefix: canon-outputs/

log_level: INFO
```

> Toil-specific options (batch_system, default_memory, etc.) are configured in the `toil_options:` block defined by the `canon-executor-toil` plugin, not in core `canon.yaml`. See the `canon-executor-toil` documentation.

---

## Validation Error Reference

All `CanonConfigError` conditions raised during config loading:

| Condition | Error message |
|---|---|
| `mosaic_url` missing | `canon.yaml: mosaic_url is required` |
| `mosaic_url` not a valid URI | `canon.yaml: mosaic_url must be an http or https URI` |
| Mosaic unreachable at startup | `canon.yaml: cannot reach Mosaic at {mosaic_url}/health — {detail}` |
| Incompatible Mosaic version | `canon.yaml: Mosaic version {v} is not supported (requires ≥ 0.1.0)` |
| Canon entity types missing from Mosaic | `canon.yaml: Canon entity types not found in Mosaic schema. Run: hippo reference install canon` |
| `mosaic_token` missing | `canon.yaml: mosaic_token is required` |
| `mosaic_token` env var not set | `canon.yaml: environment variable {VAR} is not set` |
| `executor` missing | `canon.yaml: executor is required` |
| `executor` value not recognized | `canon.yaml: executor '{name}' not found. Available: {list}` |
| Executor binary unavailable | `canon.yaml: executor '{name}' is configured but not available — {detail}` |
| `output_storage` missing | `canon.yaml: output_storage is required` |
| `output_storage.type` unknown | `canon.yaml: output_storage.type must be one of: local, s3` |
| `output_storage.base_path` not writable | `canon.yaml: output_storage.base_path {path} is not writable` |
| `output_storage` S3 probe failed | `canon.yaml: output_storage S3 bucket {bucket} is not accessible — {detail}` |
| `rules_file` not found | `canon.yaml: rules file not found: {path}` |
| `log_level` invalid | `canon.yaml: log_level must be one of: DEBUG, INFO, WARNING, ERROR` |
| `cwltool_options` is not a list | `canon.yaml: cwltool_options must be a list of strings` |
