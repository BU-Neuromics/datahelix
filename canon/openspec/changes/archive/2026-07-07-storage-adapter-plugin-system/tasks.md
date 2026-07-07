## Tasks

### Phase 1: Core Infrastructure (TDD — write tests first)

- [x] Add `CanonStorageError` to `canon/exceptions.py` (subclass of `CanonError`)
- [x] Create `canon/storage/__init__.py` with public exports
- [x] Create `canon/storage/base.py` with `StorageAdapter` ABC — `put()`, `get()`, `exists()` abstract methods, `build_dest_uri()` with `NotImplementedError` default, `name` and `uri_schemes` class attrs
- [x] Create `canon/tests/test_storage.py` with RED tests for ABC (cannot instantiate, has required attrs)
- [x] Create `canon/storage/local.py` with `LocalStorageAdapter` — `put()` (shutil.copy2, mkdir parents), `get()` (return path if exists, raise CanonStorageError if not), `exists()` (Path.exists()), `build_dest_uri()` (base_path/entity_type/id/filename)
- [x] Add RED unit tests for `LocalStorageAdapter` (put copies file, get returns path, exists true/false, build_dest_uri format, put raises on missing source, get raises on missing URI, handles file:// and bare paths)
- [x] Run tests — confirm all RED tests fail
- [x] Implement until all storage unit tests pass (GREEN)

### Phase 2: Registry

- [x] Create `canon/storage/registry.py` with `StorageAdapterRegistry` — `load_from_entry_points()`, `adapter_for_uri()`, `default_adapter` property
- [x] Add RED unit tests for registry — routes file:// to local, routes bare paths to local, raises CanonConfigError on unknown scheme, raises on unknown type, default_adapter returns configured adapter
- [x] Implement until all registry tests pass (GREEN)

### Phase 3: Executor Adapter Flags

- [x] Add `requires_local_staging: bool = True` and `requires_output_relocation: bool = True` to `CWLExecutorAdapter` in `executors/base.py`
- [x] Add unit tests verifying `CwltoolAdapter` inherits both as `True`
- [x] Run existing executor tests — confirm no regressions

### Phase 4: Pipeline Integration

- [x] Modify `OutputIngestionPipeline.__init__` to accept `StorageAdapter` (or `StorageAdapterRegistry`)
- [x] Replace `relocate_output()` type-branching with `storage_adapter.put()` delegation
- [x] Remove the `type: s3` warning stub
- [x] Add unit tests: pipeline calls `put()` when `requires_output_relocation=True`, pipeline skips `put()` when flag is `False`, pipeline propagates `CanonStorageError`
- [x] Run existing `test_ingestion.py` — fix any regressions from constructor change

### Phase 5: Config and Entry Point

- [x] Update `CanonConfig` to validate `output_storage.type` and pass extra fields through
- [x] Add `canon.storage_adapters` entry point group to `pyproject.toml` with `local` registered
- [x] Add integration test: entry point discovery loads `LocalStorageAdapter`

### Phase 6: Full Suite Validation

- [x] Run `cd canon && uv run pytest tests/ -v` — all Canon tests pass
- [x] Run `make test` at monorepo root — all 3 tiers pass (no regressions)
- [x] Commit Canon-only changes: `feat(canon): storage adapter plugin system — StorageAdapter ABC, LocalStorageAdapter, registry`

### Post-Implementation TODOs (separate commits)

- [x] Add `tests/contracts/test_storage_adapter_contract.py` — behavioral contract for StorageAdapter ABC (landed; passing in the 2026-07-07 contract-tier run)
- [x] Add platform-level storage tests to `tests/platform/test_canon_platform.py` (landed; passing in the 2026-07-07 platform-tier run)
- [x] Update project notes and memory (close-out recorded in DataHelix epic #38; specs synced to `openspec/specs/`)
