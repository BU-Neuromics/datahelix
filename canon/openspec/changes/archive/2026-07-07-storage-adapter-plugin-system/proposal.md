## Why

Canon v0.1 has a hard-coded `type: local` branch and an S3 warning stub in `OutputIngestionPipeline.relocate_output()`. Adding any new storage backend (S3, GCS, iRODS) requires modifying Canon core. This makes Canon unusable in AWS environments — our primary production target — on day 1. We need a pluggable storage adapter system so storage backends can be implemented as independent packages, following the same entry-point pattern already established for executor adapters.

## What Changes

- **New `StorageAdapter` ABC** — `put()`, `get()`, `exists()`, `build_dest_uri()` methods with `uri_schemes` declaration
- **New `LocalStorageAdapter`** — bundled implementation replacing the current v0.1 local stub
- **New `StorageAdapterRegistry`** — entry-point discovery (`canon.storage_adapters`) with URI-scheme routing
- **Modified `OutputIngestionPipeline`** — delegates to `StorageAdapterRegistry` instead of hard-coded type branches; **BREAKING** removes the old `type: local / type: s3` branching
- **Modified `CWLExecutorAdapter` ABC** — adds `requires_local_staging` and `requires_output_relocation` class vars to decouple storage concerns from execution concerns
- **Modified `CwltoolAdapter`** — sets both flags to `True` (local executor needs Canon to handle staging)
- **Modified `canon.yaml` config schema** — `output_storage.type` maps to entry point name; adapter-specific extra fields passed through
- **Updated `pyproject.toml`** — adds `canon.storage_adapters` entry point group with `local` registered

## Capabilities

### New Capabilities
- `storage-adapter-abc` — StorageAdapter ABC with put/get/exists contract
- `local-storage-adapter` — Bundled LocalStorageAdapter for filesystem storage
- `storage-adapter-registry` — Entry-point discovery and URI-scheme routing
- `executor-storage-flags` — Executor adapter declares staging/relocation needs

### Modified Capabilities
- (none — this is new infrastructure; existing tests for the old pipeline.py behavior will be updated in tasks)

## Impact

- **Code:** New `canon/storage/` package (3 modules); modified `ingestion/pipeline.py`, `executors/base.py`, `executors/cwltool.py`, `config.py`
- **Config:** `output_storage` section gains adapter-specific fields; `type: local` still works identically
- **Dependencies:** No new external dependencies (LocalStorageAdapter uses stdlib `shutil`)
- **Breaking:** The old `type: s3` warning stub is removed; S3 support requires installing `canon-storage-s3` (external package, not part of this change)
- **Tests:** New unit tests in `canon/tests/test_storage.py`; existing pipeline tests updated
