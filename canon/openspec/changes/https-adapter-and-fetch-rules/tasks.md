## Tasks

### Phase 1: HTTPStorageAdapter (TDD)

- [x] Write RED tests in `tests/test_storage.py` for `HTTPStorageAdapter`:
  - `get()` downloads file (mock httpx.stream, verify file written to local_dir)
  - `get()` raises CanonStorageError on 404 response
  - `get()` raises CanonStorageError on connection error
  - `exists()` returns True on 200 HEAD response
  - `exists()` returns False on 404 HEAD response
  - `exists()` returns False on connection error (no raise)
  - `put()` raises CanonStorageError("HTTP adapter is read-only")
  - filename is derived from URI path component
  - Entry point discovery: `StorageAdapterRegistry.adapter_for_uri("https://...")` returns `HTTPStorageAdapter`
- [x] Run tests — confirm RED
- [x] Create `canon/storage/http.py` with `HTTPStorageAdapter`
- [x] Add `https` and `http` entry points to `pyproject.toml`
- [x] Run tests — confirm GREEN

### Phase 2: FetchRule DSL (TDD)

- [x] Write RED tests in `tests/test_rules.py` for fetch rules:
  - `RulesLoader` parses valid fetch rule into `FetchRule` instance
  - `FetchRule` is not an instance of `ProductionRule`
  - `RulesLoader` raises `CanonRulesError` on missing `source_uri`
  - `RulesLoader` raises `CanonRulesError` on non-https/http `source_uri` scheme
  - Mixed production + fetch rules coexist
  - `RuleRegistry.find_fetch_rule()` returns matching rule
  - `RuleRegistry.find_fetch_rule()` returns None when no match
- [x] Run tests — confirm RED
- [x] Add `FetchRule` dataclass to `canon/rules/models.py`
- [x] Update `canon/rules/loader.py` to parse `type: fetch` rules
- [x] Update `canon/rules/registry.py` to store and retrieve fetch rules
- [x] Run tests — confirm GREEN

### Phase 3: Planner FETCH Decision (TDD)

- [x] Write RED tests in `tests/test_planner.py` for FETCH outcome:
  - REUSE wins when entity uri accessible (no FETCH even if rule exists)
  - FETCH triggered when entity uri absent + fetch rule matches
  - FETCH triggered when entity uri inaccessible + fetch rule matches
  - FETCH triggered when no entity + fetch rule matches
  - BUILD triggered when no entity + production rule (no fetch rule)
  - FAIL when no entity + no rule of any type
  - Skip download when `storage_adapter.exists(dest_uri)` True → no `get()` called
  - Download proceeds when dest absent → `get()` + `put()` called
  - Checksum match → proceeds
  - Checksum mismatch → raises CanonStorageError, entity not updated
  - `FetchCompleted` event data on entity after download
  - `FetchSkipped` event data on entity when dest exists
  - `plan()` returns PlanNode with `decision="FETCH"` and `source_uri` in metadata
- [x] Run tests — confirm RED
- [x] Implement FETCH branch in `canon/resolver/planner.py`
  - `_plan_internal()`: check REUSE → FETCH → BUILD → FAIL
  - `_execute_fetch()`: skip-if-cached, download, checksum verify, put, update_entity
- [x] Run tests — confirm GREEN

### Phase 4: Full Suite Validation

- [x] Run `cd canon && uv run pytest tests/ -v --tb=short` — all Canon tests pass (133 passed)
- [ ] Run `make test` at monorepo root — all 3 tiers pass, no regressions
- [ ] Commit Canon-only changes: `feat(canon): HTTP adapter and fetch rules — REUSE/FETCH/BUILD/FAIL planner`

### Post-Implementation TODOs (separate commits)

- [ ] Add `tests/contracts/test_storage_adapter_contract.py` (from previous change todo)
- [ ] Update platform tests in `tests/platform/test_canon_platform.py` with fetch rule scenarios
- [ ] Update project notes and memory with fetch rules design decisions
