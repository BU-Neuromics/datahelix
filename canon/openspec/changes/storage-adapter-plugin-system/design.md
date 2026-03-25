## Technical Design: Storage Adapter Plugin System

### Architecture

The storage adapter system follows the same plugin pattern as Canon's executor adapters (`canon.executor_adapters` entry point group). Three new modules under `canon/storage/`:

```
canon/storage/
  __init__.py     # exports StorageAdapter, LocalStorageAdapter, StorageAdapterRegistry
  base.py         # StorageAdapter ABC + CanonStorageError
  local.py        # LocalStorageAdapter (bundled)
  registry.py     # StorageAdapterRegistry (discovery + routing)
```

### Key Decisions

1. **CanonStorageError lives in `canon/exceptions.py`** — consistent with all other Canon exceptions (`CanonConfigError`, `CanonCycleError`, etc.). It subclasses the existing `CanonError` base.

2. **`StorageAdapterRegistry` is instantiated in `RecursivePlanner.__init__`** and passed to `OutputIngestionPipeline`. This avoids global state and makes testing easy (inject a registry with a mock adapter).

3. **`build_dest_uri()` is a method on the adapter, not the pipeline** — each backend has its own URI construction conventions (S3 key naming differs from local path layout).

4. **`get()` for LocalStorageAdapter returns the path as-is when accessible** — for shared filesystems (NFS), the file is already local. Only copies to `local_dir` if the original path doesn't exist (node-local execution without shared FS).

5. **Config passthrough** — `CanonConfig.output_storage` becomes a dict with `type` plus arbitrary extra fields. The registry extracts `type` to find the entry point, then passes the remaining fields to the adapter constructor. This allows adapter-specific config (S3 bucket, GCS credentials) without Canon core knowing about them.

6. **`uri_schemes` enables mixed-backend input staging** — a pipeline can have inputs from `s3://` and outputs to `file://`. The registry routes each URI to the correct adapter by scheme prefix.

### Modified Components

**`canon/executors/base.py`:**
- Add `requires_local_staging: bool = True` and `requires_output_relocation: bool = True` class attributes to `CWLExecutorAdapter`

**`canon/executors/cwltool.py`:**
- No changes needed — inherits the `True` defaults from the ABC

**`canon/ingestion/pipeline.py`:**
- Constructor accepts `storage_adapter: StorageAdapter` (or `StorageAdapterRegistry`)
- `relocate_output()` calls `storage_adapter.put()` instead of branching on `type`
- Remove the `type: s3` warning stub
- Remove the `type: local` hard-coded copy logic

**`canon/config.py`:**
- `output_storage` remains a config section; `type` field is required, extra fields are adapter-specific

**`pyproject.toml`:**
- Add `[project.entry-points."canon.storage_adapters"]` with `local = "canon.storage.local:LocalStorageAdapter"`

### Test Strategy

**Unit tests (`canon/tests/test_storage.py`):**
- `StorageAdapter` ABC — cannot instantiate directly
- `LocalStorageAdapter.put()` — copies file, returns `file://` URI, creates dirs
- `LocalStorageAdapter.get()` — returns path as-is if exists, raises if not
- `LocalStorageAdapter.exists()` — true/false for present/absent files
- `LocalStorageAdapter.build_dest_uri()` — correct path construction
- `StorageAdapterRegistry.adapter_for_uri()` — correct routing by scheme
- `StorageAdapterRegistry` — raises on unknown scheme/type
- `CanonStorageError` — is a subclass of `CanonError`

**Integration with existing tests:**
- Existing `test_ingestion.py` tests that mock `relocate_output()` should still pass
- New tests verify the pipeline delegates to the adapter correctly
