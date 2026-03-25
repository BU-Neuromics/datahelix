# Section 5b: Storage Adapters

**Status:** Design complete — v0.2 target  
**Last updated:** 2026-03-25

---

## Overview

Canon v0.1 contains a stub `output_storage` config with hard-coded `type: local` and a warning stub for `type: s3`. This section specifies the full pluggable storage adapter system for v0.2.

**The core insight:** storage is a concern of *Canon core* (where do outputs persist? where do inputs come from?), but staging (making files locally accessible for an executor) is a concern of *executor adapters* (does this executor need local files, or can it access storage natively?). These two concerns are cleanly separated.

---

## Why a Plugin Architecture

Different execution environments require different storage backends:
- Single workstation → local filesystem
- Academic HPC cluster → NFS shared filesystem (still "local" semantically)
- AWS cloud → S3
- GCP cloud → GCS
- Academic data repository → OSF, iRODS

Canon core should not hard-code any of these. Community contributors should be able to publish `canon-storage-s3`, `canon-storage-gcs`, `canon-storage-irods` etc. as independent packages, following the same pattern already established for executor adapters (`canon.executor_adapters` entry point group).

---

## StorageAdapter ABC

**Location:** `canon/storage/base.py`

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class StorageAdapter(ABC):
    """Abstract base class for Canon storage backends.

    Responsible for:
    - put(): relocating CWL output files to permanent storage, returning canonical URI
    - get(): staging a URI to a local path (for executors that need local files)
    - exists(): checking whether a URI is accessible (used by planner REUSE decision)

    NOT responsible for:
    - Input validation or schema enforcement (Hippo's concern)
    - Workflow execution (executor adapter's concern)
    - Whether staging is needed (executor adapter declares this via requires_local_staging)
    """

    #: Entry point name, e.g. "local", "s3", "gcs". Must be unique.
    name: str

    #: URI schemes this adapter handles, e.g. ["file", "s3", "s3a"].
    uri_schemes: list[str]

    @abstractmethod
    def put(self, local_path: Path, dest_uri: str) -> str:
        """Relocate a local file to permanent storage.

        Called by OutputIngestionPipeline after CWL execution completes,
        when executor.requires_output_relocation is True.

        Args:
            local_path: Path to the file in the CWL work directory.
            dest_uri: Target URI (constructed from output_storage config + entity identity).

        Returns:
            Canonical URI of the relocated file (may differ from dest_uri
            if the backend rewrites it, e.g. to add a version hash).

        Raises:
            CanonStorageError: On any storage backend failure.
        """
        ...

    @abstractmethod
    def get(self, uri: str, local_dir: Path) -> Path:
        """Stage a file from permanent storage to a local directory.

        Called by InputStagingLayer before CWL execution,
        when executor.requires_local_staging is True.

        For local adapters where the URI is already a filesystem path,
        this is typically a no-op (return the path as-is) or a copy
        to node-local tmp.

        Args:
            uri: Canonical URI of the file to stage.
            local_dir: Target directory for the staged file.

        Returns:
            Local path to the staged file.

        Raises:
            CanonStorageError: On any storage backend failure.
        """
        ...

    @abstractmethod
    def exists(self, uri: str) -> bool:
        """Check whether a URI is accessible in this storage backend.

        Called by RecursivePlanner before making a REUSE vs BUILD decision.
        A URI that exists in Hippo metadata but is not accessible in storage
        should return False (triggers rebuild, not silent failure).

        Args:
            uri: Canonical URI to check.

        Returns:
            True if the file exists and is accessible.
        """
        ...

    def build_dest_uri(self, entity_type: str, entity_id: str, filename: str) -> str:
        """Construct a canonical destination URI for a new output file.

        Default implementation: subclasses may override for backend-specific
        URI construction (e.g. S3 key naming conventions).

        Args:
            entity_type: Hippo entity type of the output (e.g. "AlignmentFile").
            entity_id: Hippo entity UUID.
            filename: Original filename from CWL output.

        Returns:
            Canonical URI string.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build_dest_uri()"
        )
```

---

## Bundled Adapter: LocalStorageAdapter

**Location:** `canon/storage/local.py`  
**Entry point:** `canon.storage_adapters` → `local`  
**URI schemes:** `file://`, bare paths

```python
class LocalStorageAdapter(StorageAdapter):
    name = "local"
    uri_schemes = ["file", ""]  # empty string = bare filesystem path

    def __init__(self, base_path: str | Path) -> None:
        self._base = Path(base_path)

    def put(self, local_path: Path, dest_uri: str) -> str:
        dest = self._uri_to_path(dest_uri)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        return f"file://{dest}"

    def get(self, uri: str, local_dir: Path) -> Path:
        src = self._uri_to_path(uri)
        # For NFS/shared filesystems, the file is already accessible — return as-is.
        # For node-local execution without shared FS, caller should pass a different
        # local_dir and we copy; but by default trust the path is accessible.
        if src.exists():
            return src
        # Fall back to copy to local_dir
        dest = local_dir / src.name
        shutil.copy2(src, dest)
        return dest

    def exists(self, uri: str) -> bool:
        return self._uri_to_path(uri).exists()

    def build_dest_uri(self, entity_type: str, entity_id: str, filename: str) -> str:
        dest = self._base / entity_type.lower() / entity_id / filename
        return f"file://{dest}"

    def _uri_to_path(self, uri: str) -> Path:
        return Path(uri.removeprefix("file://"))
```

**Coverage of LocalStorageAdapter:**

| Scenario | Behavior |
|----------|----------|
| Single workstation | `get()` returns path as-is (no copy). |
| HPC cluster, shared NFS | Same — path accessible on all nodes. |
| HPC cluster, no shared FS | `get()` copies to node-local `local_dir`. |
| CWL work dir cleanup | After `put()`, caller is responsible for cleaning work dir. |

---

## Community Plugin: S3StorageAdapter (example, not bundled)

**Package:** `canon-storage-s3` (separate PyPI package)  
**Entry point:** `canon.storage_adapters` → `s3`  
**URI schemes:** `s3://`, `s3a://`

```python
# pyproject.toml of canon-storage-s3:
[project.entry-points."canon.storage_adapters"]
s3 = "canon_storage_s3:S3StorageAdapter"
```

```python
class S3StorageAdapter(StorageAdapter):
    name = "s3"
    uri_schemes = ["s3", "s3a"]

    def __init__(self, bucket: str, prefix: str = "", credentials: str = "env") -> None:
        self._bucket = bucket
        self._prefix = prefix
        # credentials: "env" | "instance_role" | "profile:<name>"
        self._client = _build_boto3_client(credentials)

    def put(self, local_path: Path, dest_uri: str) -> str:
        key = self._uri_to_key(dest_uri)
        self._client.upload_file(str(local_path), self._bucket, key)
        return f"s3://{self._bucket}/{key}"

    def get(self, uri: str, local_dir: Path) -> Path:
        key = self._uri_to_key(uri)
        dest = local_dir / Path(key).name
        self._client.download_file(self._bucket, key, str(dest))
        return dest

    def exists(self, uri: str) -> bool:
        key = self._uri_to_key(uri)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._client.exceptions.ClientError:
            return False
```

---

## Executor Adapter Integration

`CWLExecutorAdapter` declares whether it needs Canon to handle staging:

```python
class CWLExecutorAdapter(ABC):
    #: If True, Canon's InputStagingLayer will call storage_adapter.get() for all
    #: non-local input URIs before execution. Set False for cloud-native executors
    #: (Nextflow, Toil on AWS Batch) that access storage URIs natively.
    requires_local_staging: bool = True

    #: If True, Canon's OutputIngestionPipeline will call storage_adapter.put() to
    #: relocate CWL work dir outputs to permanent storage. Set False for executors
    #: that write directly to permanent storage (e.g. Nextflow with publishDir).
    requires_output_relocation: bool = True
```

**Current adapters:**

| Adapter | `requires_local_staging` | `requires_output_relocation` |
|---------|--------------------------|------------------------------|
| `CwltoolAdapter` (bundled) | `True` | `True` |
| `NextflowAdapter` (future plugin) | `False` | `False` |
| `ToilAdapter` (future plugin) | Depends on backend | `True` for local, `False` for cloud |

**Canon pipeline with storage adapters:**

```
RecursivePlanner.resolve(entity_type, params)
    │
    ├─ hippo_client.find_entity() → entity found?
    │       YES → return entity.uri (REUSE)
    │       NO  → continue to BUILD
    │
    ├─ storage_adapter.exists(input_uri) for each required input
    │       (validates inputs are accessible before committing to a build)
    │
    ├─ [if executor.requires_local_staging]
    │       InputStagingLayer.stage(inputs, storage_adapter)
    │           → storage_adapter.get(uri, work_dir) for each non-local URI
    │
    ├─ executor.run(cwl_path, staged_inputs, work_dir)
    │       → CWLRunResult(outputs, exit_code, ...)
    │
    ├─ [if executor.requires_output_relocation]
    │       storage_adapter.put(local_output_path, dest_uri)
    │           → canonical_uri
    │
    └─ hippo_client.ingest_entity(entity_type, {uri: canonical_uri, ...})
           → Entity
```

---

## StorageAdapterRegistry

**Location:** `canon/storage/registry.py`

Discovers adapters via entry points and routes URIs to the correct adapter by scheme:

```python
class StorageAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, StorageAdapter] = {}

    def load_from_entry_points(self) -> None:
        for ep in importlib.metadata.entry_points(group="canon.storage_adapters"):
            adapter_cls = ep.load()
            adapter = adapter_cls(...)  # instantiated from CanonConfig
            for scheme in adapter.uri_schemes:
                self._adapters[scheme] = adapter

    def adapter_for_uri(self, uri: str) -> StorageAdapter:
        scheme = uri.split("://")[0] if "://" in uri else ""
        try:
            return self._adapters[scheme]
        except KeyError:
            raise CanonConfigError(
                f"No storage adapter registered for URI scheme '{scheme}'. "
                f"Install a canon-storage-* package or check your canon.yaml output_storage.type."
            )
```

---

## Config Schema (canon.yaml)

The `output_storage` section is extended to support adapter-specific config:

```yaml
# Local filesystem (bundled default)
output_storage:
  type: local
  base_path: /data/outputs

# S3 (requires pip install canon-storage-s3)
output_storage:
  type: s3
  bucket: my-lab-canon-outputs
  prefix: outputs/
  credentials: instance_role   # "env" | "instance_role" | "profile:<name>"

# GCS (requires pip install canon-storage-gcs)
output_storage:
  type: gcs
  bucket: my-lab-canon-outputs
  prefix: outputs/
  credentials: application_default
```

The `type` field maps directly to the entry point name. Unknown types raise `CanonConfigError` at startup with a helpful message listing available adapters.

---

## Error Handling and Atomicity

A storage failure mid-pipeline creates a consistency risk: outputs may be relocated but the Hippo entity record not written (or vice versa).

**Protocol:**
1. `put()` is called before `ingest_entity()`.
2. If `put()` fails → raise `CanonStorageError`; WorkflowRun is marked `failed`; no Hippo entity written; output file may or may not exist in storage depending on where the failure occurred.
3. If `put()` succeeds but `ingest_entity()` fails → output file exists in storage without a Hippo record. This is an **orphan artifact**.
4. Canon does not automatically clean up orphan artifacts (storage may be read-only, deletion may be unsafe).
5. WorkflowRun is marked `failed` with `error_detail` including the storage URI so operators can manually recover.

**Future mitigation (v0.3):** Two-phase commit pattern — write a `PendingArtifact` record to Hippo before `put()`, update to `confirmed` after `ingest_entity()` succeeds. Orphan detection via `hippo query PendingArtifact status=pending created_before=<24h_ago>`.

---

## Implementation Plan (v0.2)

**New files:**
- `canon/storage/__init__.py`
- `canon/storage/base.py` — `StorageAdapter` ABC + `CanonStorageError`
- `canon/storage/local.py` — `LocalStorageAdapter` (replaces current v0.1 stub)
- `canon/storage/registry.py` — `StorageAdapterRegistry`

**Modified files:**
- `canon/ingestion/pipeline.py` — replace `type: local / type: s3 warn()` with `registry.adapter_for_uri(dest_uri).put()`
- `canon/executors/base.py` — add `requires_local_staging` and `requires_output_relocation` class vars
- `canon/executors/staging.py` — update `InputStagingLayer` to accept `StorageAdapter` and call `.get()`
- `canon/config.py` — extend `output_storage` to support adapter-specific extra fields
- `canon/resolver/planner.py` — add `storage_adapter.exists()` pre-flight check on inputs
- `pyproject.toml` — add `canon.storage_adapters` entry point group, register `local`

**External packages (separate repos, community-contributed):**
- `canon-storage-s3` — `S3StorageAdapter` (boto3)
- `canon-storage-gcs` — `GCSStorageAdapter` (google-cloud-storage)
- `canon-storage-osf` — `OSFStorageAdapter` (reuse dvc-osf client logic)
- `canon-storage-irods` — `iRODSStorageAdapter` (python-irodsclient)

**Test additions:**
- `canon/tests/test_storage.py` — unit tests for `LocalStorageAdapter` and `StorageAdapterRegistry`
- `tests/contracts/test_storage_adapter_contract.py` — behavioral contract for `StorageAdapter` ABC
- `tests/platform/test_canon_platform.py` — extend with storage adapter tests using `LocalStorageAdapter`
