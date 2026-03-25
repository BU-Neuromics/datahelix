## Technical Design: HTTPS Adapter and Fetch Rules

### Architecture

Two self-contained changes that compose cleanly:

1. **HTTPStorageAdapter** — thin read-only adapter, ~50 lines. Uses `httpx` (already a Canon dep). Registered in entry points alongside `local`.

2. **Fetch rules** — new rule variant threaded through the existing rules → registry → planner pipeline. The planner already has a REUSE/BUILD binary; FETCH inserts between them.

### Key Decisions

**1. FETCH decision ordering (REUSE → FETCH → BUILD → FAIL)**

FETCH is checked *before* BUILD because if we have a fetch rule and the entity metadata is in Hippo (from `hippo reference install`), we should always prefer fetching the known file over trying to compute it. BUILD is only for entities that have no pre-existing source.

**2. Hippo entity as the single source of truth — Canon sets `uri`, not `source_uri`**

`hippo reference install` sets `source_uri` (and optionally `checksum_sha256`) as part of semantic registration. Canon reads `source_uri` from the entity (via Hippo query) to know where to download from. Canon sets `uri` after materialization. This avoids the need to put `source_uri` in the `FetchRule` at all if the entity already has it — but the `FetchRule` also carries `source_uri` as a fallback for when no entity exists yet (the "no entity, fetch rule exists" FETCH branch).

*Decision: `FetchRule.source_uri` is the authoritative source for the download URL. If the entity exists and has `source_uri`, both point to the same place. We do NOT read `source_uri` from the entity at fetch time — the rule is the contract.*

Rationale: entity data in Hippo is mutable and could diverge from the rule. The rule in `canon_rules.yaml` is under version control and is the reproducibility contract.

**3. Destination URI construction**

The `storage_adapter.build_dest_uri()` method is called to determine where the downloaded file will live in permanent storage. This means the same `LocalStorageAdapter` or `S3StorageAdapter` handles all Canon-managed files — reference data and computed data live in the same storage tree. No separate "reference cache" path.

**4. Skip-if-cached logic — `exists(dest_uri)`, not `exists(entity.uri)`**

We check whether the *destination URI* (where we'd put the file) already exists, not whether the entity's current URI exists. This handles the case where the entity has a stale/wrong URI but the file is already at the correct destination.

**5. Provenance: update_entity on the entity, not a separate WorkflowRun**

Fetch operations are lighter-weight than CWL executions. They don't need a `WorkflowRun` entity. Instead, we record the fetch event as a field update on the entity itself (`FetchCompleted` / `FetchSkipped` in the entity's `data` dict or provenance log). This keeps the entity self-describing.

*Concrete: after fetch, call `hippo_client.update_entity(entity_id, {**existing_data, "uri": canonical_uri, "last_fetched_at": now, "fetch_status": "completed"})`*

**6. `FetchRule` vs `ProductionRule` — separate dataclasses, not a union type**

`FetchRule` and `ProductionRule` are distinct dataclasses. The `RuleRegistry` stores them in separate dicts and exposes `find_rule()` (production) and `find_fetch_rule()` (fetch). The planner calls both and picks the right one. This avoids type-switching logic and keeps the dataclasses focused.

### Modified Components

**`canon/storage/http.py`** (new):
- `HTTPStorageAdapter` with `httpx.stream` for `get()`, `httpx.head` for `exists()`, CanonStorageError for `put()`
- Filename derived from `uri.split("/")[-1]`

**`canon/rules/models.py`**:
- Add `FetchRule(name, produces, source_uri, checksum_sha256=None)` dataclass

**`canon/rules/loader.py`**:
- Handle `type: fetch` in `_parse_rule()` — validate `fetch.source_uri` present and scheme is https/http
- Return `FetchRule` instances

**`canon/rules/registry.py`**:
- Add `_fetch_rules: dict[str, FetchRule]` storage
- Add `find_fetch_rule(entity_type, params) -> FetchRule | None`
- `register_rule()` dispatches to correct dict based on isinstance

**`canon/resolver/planner.py`**:
- `_plan_internal()` — add FETCH branch between REUSE and BUILD
- FETCH execution: check `exists(dest_uri)`, conditionally download, verify checksum, call `put()`, call `hippo_client.update_entity()`
- `PlanNode.decision` — add `"FETCH"` as valid value

**`canon/pyproject.toml`**:
- Add `https = "canon.storage.https:HTTPStorageAdapter"` and `http = "canon.storage.https:HTTPStorageAdapter"` to `canon.storage_adapters`

### Test Strategy

**Unit tests — `test_storage.py`** (extend existing):
- `HTTPStorageAdapter.get()` — mock httpx, verify streaming download
- `HTTPStorageAdapter.exists()` — mock HEAD responses, True/False/network error
- `HTTPStorageAdapter.put()` — raises CanonStorageError
- Entry point discovery includes `https` and `http`

**Unit tests — `test_rules.py`** (extend existing):
- `RulesLoader` parses fetch rule correctly
- `RulesLoader` raises on missing `source_uri`
- `RulesLoader` raises on non-https scheme in `source_uri`
- Mixed production + fetch rules parse correctly
- `RuleRegistry.find_fetch_rule()` match and no-match cases

**Unit tests — `test_planner.py`** (extend existing):
- FETCH decision when entity exists with no `uri` + fetch rule
- FETCH decision when entity exists with inaccessible `uri` + fetch rule
- REUSE decision wins over FETCH when `uri` accessible
- BUILD when no entity, no fetch rule, production rule exists
- Skip download when `exists(dest_uri)` returns True
- Checksum mismatch raises CanonStorageError
- `FetchCompleted` event recorded on entity after download
- `FetchSkipped` event recorded when dest exists
- `plan()` returns FETCH decision node
