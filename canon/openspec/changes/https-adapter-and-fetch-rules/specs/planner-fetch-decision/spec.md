## ADDED Requirements

### Requirement: RecursivePlanner supports FETCH as a fourth resolution outcome

The `RecursivePlanner` SHALL recognize four resolution outcomes, evaluated in this order:
1. **REUSE** — entity found in Hippo AND `uri` field present AND `storage_adapter.exists(uri)` returns True
2. **FETCH** — entity found in Hippo AND (`uri` absent OR `exists(uri)` returns False) AND a matching `FetchRule` exists; OR no entity found AND a matching `FetchRule` exists
3. **BUILD** — no entity found AND a matching `ProductionRule` exists
4. **FAIL** — no entity found AND no applicable rule of any type → raise `CanonNoRuleError`

#### Scenario: REUSE when entity has accessible URI
- **WHEN** Hippo has a `GenomeBuild` entity with `uri = "file:///data/GRCh38.fa"` and that path exists
- **THEN** `resolve()` SHALL return the URI immediately without downloading or executing

#### Scenario: FETCH when entity exists but uri absent
- **WHEN** Hippo has a `GenomeBuild` entity with no `uri` field AND a fetch rule matches
- **THEN** `resolve()` SHALL download the file and update the entity `uri`

#### Scenario: FETCH when entity exists but uri not accessible
- **WHEN** Hippo has a `GenomeBuild` entity with `uri = "file:///old/path/GRCh38.fa"` but that file doesn't exist, AND a fetch rule matches
- **THEN** `resolve()` SHALL download fresh and update the entity `uri` to the new canonical location

#### Scenario: FAIL when no entity and no applicable rule
- **WHEN** Hippo has no matching entity AND no production or fetch rule matches
- **THEN** `resolve()` SHALL raise `CanonNoRuleError`

### Requirement: FETCH execution skips download if destination already cached

During FETCH execution, the planner SHALL construct the destination URI via `storage_adapter.build_dest_uri()` and check whether it already exists before downloading.

#### Scenario: Skip download when destination already exists
- **WHEN** FETCH is triggered and `storage_adapter.exists(dest_uri)` returns True
- **THEN** the planner SHALL NOT call `https_adapter.get()` and SHALL only update the entity `uri` if not already set; a `FetchSkipped` provenance event SHALL be recorded on the entity

#### Scenario: Download when destination absent
- **WHEN** FETCH is triggered and `storage_adapter.exists(dest_uri)` returns False
- **THEN** the planner SHALL call `https_adapter.get(source_uri, work_dir)` to download the file, then `storage_adapter.put(local_path, dest_uri)` to relocate it; a `FetchCompleted` provenance event SHALL be recorded on the entity

### Requirement: Checksum verification after download

If `FetchRule.checksum_sha256` is set, the planner SHALL verify the downloaded file's SHA-256 checksum before calling `storage_adapter.put()`.

#### Scenario: Checksum matches — proceed
- **WHEN** downloaded file SHA-256 matches `FetchRule.checksum_sha256`
- **THEN** relocation and entity update SHALL proceed normally

#### Scenario: Checksum mismatch — raise CanonStorageError
- **WHEN** downloaded file SHA-256 does NOT match `FetchRule.checksum_sha256`
- **THEN** a `CanonStorageError` SHALL be raised with expected vs actual checksums; the local temp file SHALL be deleted; the entity SHALL NOT be updated

### Requirement: FETCH records provenance events on the entity

After a FETCH operation (download or skip), the planner SHALL record a provenance event on the Hippo entity via `hippo_client.update_entity()`.

#### Scenario: FetchCompleted event recorded after successful download
- **WHEN** a file is newly downloaded and entity `uri` updated
- **THEN** the entity record in Hippo SHALL have an updated `uri` field AND a `FetchCompleted` event SHALL be recorded containing `source_uri`, `canonical_uri`, `checksum_sha256` (if verified), and timestamp

#### Scenario: FetchSkipped event recorded when destination exists
- **WHEN** destination already exists and only `uri` update is needed (or uri already correct)
- **THEN** a `FetchSkipped` event SHALL be recorded containing `source_uri`, `dest_uri`, and timestamp

### Requirement: plan() dry-run reflects FETCH decisions

The `plan()` method SHALL represent FETCH as a distinct decision type in the returned `PlanNode`, separate from REUSE and BUILD.

#### Scenario: plan() returns FETCH decision for entity without uri
- **WHEN** `plan()` is called for an entity type with a matching fetch rule and entity has no uri
- **THEN** the returned `PlanNode` SHALL have `decision = "FETCH"` with `source_uri` in the plan metadata
