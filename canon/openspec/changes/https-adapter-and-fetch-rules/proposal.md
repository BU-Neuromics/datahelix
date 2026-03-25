## Why

Canon cannot currently stage files from public HTTPS URIs (reference genomes, public datasets, pre-signed URLs, DRS access URLs). More importantly, there is no mechanism for Canon to automatically download and cache reference data that has been semantically registered in Hippo via `hippo reference install` but not yet materialized locally. This means pipelines that depend on reference genomes fail at staging even when the canonical source is known. The two changes here are tightly coupled: the HTTP adapter is the download mechanism, and fetch rules are how Canon knows *when* and *what* to download.

## What Changes

**HTTPStorageAdapter (new, bundled):**
- **New** `canon/storage/http.py` — `HTTPStorageAdapter` implementing `StorageAdapter`
- Read-only adapter: `get()` (httpx streaming download) and `exists()` (HEAD request) are implemented; `put()` and `build_dest_uri()` raise `CanonStorageError` (HTTPS is a source, not a destination)
- Registered as `https` and `http` in `canon.storage_adapters` entry points

**Fetch rules (new rule type in DSL):**
- **New** `type: fetch` variant in `canon_rules.yaml` DSL
- **Modified** `canon/rules/models.py` — `FetchRule` dataclass with `source_uri` and optional `checksum_sha256`
- **Modified** `canon/rules/loader.py` — parses and validates fetch rules
- **Modified** `canon/rules/registry.py` — stores and retrieves fetch rules alongside production rules

**Planner FETCH decision (new outcome):**
- **Modified** `canon/resolver/planner.py` — adds FETCH as a fourth resolution outcome:
  - REUSE: entity found AND `uri` present AND `exists(uri)` → return URI immediately
  - FETCH: entity found AND (`uri` absent OR NOT `exists(uri)`) AND fetch rule exists → download, cache, update URI
  - BUILD: no entity found AND production rule exists → run CWL workflow
  - FAIL: no entity found AND no applicable rule
- FETCH execution: skip download if destination already exists (`exists(dest_uri)`); download fresh otherwise; verify checksum if declared; update entity `uri`; record provenance event

**Provenance events (two new event types):**
- `FetchCompleted` — recorded when file is newly downloaded and entity URI updated
- `FetchSkipped` — recorded when destination already exists and only URI update was needed

## Capabilities

### New Capabilities
- `https-storage-adapter` — HTTPStorageAdapter for staging from HTTP/HTTPS sources
- `fetch-rules-dsl` — fetch rule type in canon_rules.yaml, parsed by RulesLoader
- `planner-fetch-decision` — FETCH outcome in RecursivePlanner with skip-if-cached logic and provenance recording

### Modified Capabilities
- (none — no existing spec files to delta)

## Impact

- **Code:** New `canon/storage/http.py`; modified `rules/models.py`, `rules/loader.py`, `rules/registry.py`, `resolver/planner.py`; new provenance event types
- **Dependencies:** `httpx` (already a Canon dependency via `HippoQueryClient`) — no new packages
- **Config:** No changes — HTTP adapter auto-discovered via entry points; fetch rules are part of `canon_rules.yaml`
- **Tests:** New unit tests in `test_storage.py`; new fetch-rule tests in `test_rules.py`; updated planner tests in `test_planner.py`
- **Not in scope:** FTP adapter, multi-environment URI federation, cache TTL/invalidation, fetch rules for non-HTTP sources
