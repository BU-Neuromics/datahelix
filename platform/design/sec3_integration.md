## 3. Inter-Component Interfaces and Contracts

**Document status:** Draft v0.1
**Last updated:** 2026-03-31
**Depends on:** sec2_components.md, Mosaic sec4 (REST API), Bridge sec3 (unified API)
**Feeds into:** Platform test strategy (sec5), deployment docs, contract tests

---

### 3.1 Integration Philosophy

DataHelix components integrate through well-defined, tested interfaces. The integration contract
for each component pair is:

1. **Interface definition** — what API/SDK calls cross the boundary
2. **Contract tests** — automated tests that verify the contract is honoured from both sides
3. **Failure mode** — what happens when one side of the interface is unavailable

Components do not call each other directly except through published interfaces. There are
no internal shared modules, shared databases (except Mosaic — formerly Hippo, ADR-0004 —
as the canonical store), or shared in-process state between components.

---

### 3.2 Integration Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DataHelix Platform                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                          Bridge                               │   │
│  │   Auth enforcement, routing, actor injection, sync check     │   │
│  └──────────┬──────────────┬───────────────────┬───────────────┘   │
│             │              │                   │                     │
│       ┌─────▼────┐  ┌──────▼──────┐  ┌────────▼───────┐           │
│       │  Mosaic   │  │   Cappella  │  │     Canon      │           │
│       │          │◀─┤             │  │                │           │
│       │          │──▶  reads /    │  │  resolves via  │           │
│       │          │  │  writes     │  │  Mosaic entities│           │
│       └──────────┘  └─────────────┘  └────────────────┘           │
│             ▲                                                        │
│             │ (all data reads/writes)                                │
│       ┌─────┴────┐                                                  │
│       │ Aperture │                                                   │
│       │  (CLI)   │                                                   │
│       └──────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 3.3 Mosaic ↔ Cappella Interface

This is the most critical integration in the platform. Cappella is Mosaic's primary data
producer; Mosaic is Cappella's sole persistent store.

#### 3.3.1 Read Interface

Cappella reads entity state from Mosaic at trigger execution time via `MosaicClient` (SDK)
or Mosaic REST API (when running as a separate service).

| Operation | Interface | Contract |
|---|---|---|
| Entity lookup by ExternalID | `client.get_by_external_id(type, source, id)` | Returns entity or raises `NotFound` |
| Filtered entity list | `client.query(type, filters)` | Returns list, possibly empty |
| Entity change detection (poll) | `client.query_updated_since(type, since)` | Returns entities with `updated_at > since` |
| Fuzzy entity search | `client.search(type, query)` | Returns `ScoredMatch` list sorted by score |

#### 3.3.2 Write Interface

Cappella writes all entity data via `MosaicClient` with an explicit `actor` parameter.

| Operation | Interface | Contract |
|---|---|---|
| Create entity | `client.put(type, data, actor=actor)` | Returns entity with UUID; validates schema + validators |
| Update entity | `client.put(type, data, actor=actor)` (upsert by ExternalID) | Creates if absent, updates if changed, skips if unchanged |
| Availability change | `client.set_availability(id, False, actor=actor)` | Records supersession event in provenance |
| Relationship creation | `client.create_relationship(from_id, rel_name, to_id, actor=actor)` | Validates both entities exist; records provenance |

#### 3.3.3 Actor Convention

Cappella writes always use a meaningful `actor` value:
- Human-triggered syncs: the authenticated user's actor identity
- Scheduled/automated syncs: `service:cappella-<adapter-name>` (e.g. `service:cappella-starlims`)
- Pipeline output ingestion: `service:cappella-pipeline-<run-id>`

This convention ensures provenance records are attributable to the correct source.

#### 3.3.4 Failure Mode

If Mosaic is unavailable, Cappella's write operations fail. Cappella does not buffer writes
or retry autonomously. Operators should configure Cappella's trigger retry behavior
(`retry_on_failure: true`, `max_retries: 3`, `backoff: exponential`).

---

### 3.4 Mosaic ↔ Canon Interface

Canon resolves file artifact paths from Mosaic entity data.

#### 3.4.1 Read Interface

Canon reads entity state from Mosaic at resolution time. This is always a fresh read (no
caching of entity state in Canon).

| Operation | Interface | Contract |
|---|---|---|
| Entity fetch for resolution | `MosaicClient.get(type, entity_id)` | Required fields must be non-null |
| Batch entity fetch | `MosaicClient.batch_get(type, ids)` | Returns in-order list |

#### 3.4.2 Write Interface (Provenance Write-Back)

After resolving or producing an artifact, Canon writes a provenance event to Mosaic.

| Operation | Interface | Contract |
|---|---|---|
| Artifact resolved | `client.record_event(entity_id, "artifact_resolved", meta, actor)` | Records path, status, checksum |
| Artifact produced | `client.record_event(entity_id, "artifact_produced", meta, actor)` | Records CWL run ID, output path |
| Cache eviction | `client.record_event(entity_id, "artifact_evicted", meta, actor)` | Records reason |

#### 3.4.3 Failure Mode

If Mosaic is unavailable, Canon cannot resolve artifacts (it needs entity fields to
evaluate path templates). Canon returns `503 upstream_unavailable` from its REST API.
Provenance write-back failures are logged but do not fail the resolution response — the
file was still found/produced; the audit gap is recovered on next resolution.

---

### 3.5 Mosaic ↔ Aperture Interface

Aperture is a read-heavy client of Mosaic.

| Operation | Interface | Contract |
|---|---|---|
| Entity list | `GET /mosaic/entities/{type}` (via Bridge) or `client.query()` | Paginated; empty list if no matches |
| Entity get | `GET /mosaic/entities/{type}/{id}` | 404 if not found |
| Entity create/update | `POST/PUT /mosaic/entities/{type}/{id}` | Validates schema; returns 422 on validation failure |
| Provenance history | `GET /mosaic/entities/{type}/{id}/history` | Returns event list, newest first |
| Schema inspection | `GET /mosaic/schema` | Returns full schema definition |

Aperture is always a **client** of Mosaic — it never writes directly to Mosaic's storage
layer. In multi-user deployments, all Aperture requests pass through Bridge for auth
enforcement.

---

### 3.6 Bridge ↔ All Components Interface

Bridge is the only component that communicates with all others. Its interface with each
component is the component's REST API, augmented with injected headers.

#### 3.6.1 Routing Contract

| Bridge receives | Bridge sends to |
|---|---|
| `GET /api/v1/mosaic/*` | Mosaic REST API: `GET /*` |
| `POST /api/v1/cappella/*` | Cappella REST API: `POST /*` |
| `GET /api/v1/canon/*` | Canon REST API: `GET /*` |
| `POST/GET /api/v1/bridge/*` | Bridge itself (auth endpoints, health, metrics) |

Bridge strips the `/api/v1/{component}/` prefix before forwarding.

#### 3.6.2 Auth Middleware Contract

All components that receive requests via Bridge must implement the auth middleware
contract. When Bridge is active, each component:

1. Accepts `X-DataHelix-Actor` and `X-DataHelix-Roles` headers from Bridge's trusted network CIDR.
2. Uses `X-DataHelix-Actor` as the `actor` parameter for all writes.
3. Rejects `X-DataHelix-Actor` headers from sources outside the trusted network.
4. Falls through to the component's own auth stub when the header is absent (local dev mode).

This is implemented via the `BridgeAwareAuthMiddleware` class in `bridge.sdk.auth_middleware`.

#### 3.6.3 Failure Mode

If a component is unavailable, Bridge returns `503 component_unavailable` to the caller.
Requests to other components continue normally. Bridge does not cascade failures across
components.

---

### 3.7 Cappella ↔ Canon Interface

Cappella calls Canon to resolve and produce file artifacts as part of pipeline execution.

| Operation | Interface | Contract |
|---|---|---|
| Resolve artifact | `canon.resolve(rule, entity_id, entity_type)` | Returns path and status |
| Produce artifact | `canon.produce(rule, entity_id, entity_type)` | Blocks until CWL job completes; returns output path |
| Batch resolve | `canon.batch_resolve(rule, entity_ids)` | Returns path+status per entity |

In SDK mode (components co-located), Cappella imports `canon` directly. In service mode,
Cappella calls `GET /api/v1/canon/resolve` via Bridge.

---

### 3.8 Contract Tests

Each component pair has a corresponding contract test that verifies the interface from
both sides. Contract tests use real instances (not mocks) because DataHelix's integration
failures typically arise from assumption drift, not logic bugs.

| Test file | Contract verified |
|---|---|
| `tests/contracts/test_cappella_expects_hippo.py` | Cappella can write entities and read them back via Mosaic SDK |
| `tests/contracts/test_cappella_expects_canon.py` | Cappella can resolve artifacts for entities in Mosaic |
| `tests/contracts/test_entity_loader_contract.py` | `ExternalSourceAdapter` implementations produce entities Mosaic accepts |
| `tests/platform/test_round_trip.py` | Full round-trip: external source → Cappella → Mosaic → Canon → provenance write-back |

See `platform/design/sec5_integration_test_strategy.md` for the full test strategy.

---

### 3.9 Data Flow: End-to-End Example

Full data flow for a Cappella-driven pipeline run:

```
1. External source (STARLIMS) → Cappella (webhook trigger)
2. Cappella adapter reads source data
3. Cappella calls MosaicClient.put() for each entity (upsert by ExternalID)
   → Mosaic validates schema + validators
   → Mosaic writes entity + provenance event (actor: service:cappella-starlims)
4. Cappella trigger engine emits internal event "starlims.sync_complete"
5. Post-sync trigger fires → Cappella submits CWL pipeline via Canon
6. Canon resolves input artifacts (reads entity fields from Mosaic)
7. Canon invokes cwltool, waits for output
8. Canon writes provenance event to Mosaic (artifact_produced)
9. Cappella writes pipeline output entities to Mosaic (actor: service:cappella-pipeline-<run-id>)
10. Bridge sync engine detects run completion, verifies outputs present in Mosaic
11. Aperture user queries results: datahelix list Sample --filter cohort=CTE
```

---

### 3.10 Open Questions

| Question | Priority | Status |
|---|---|---|
| Should Cappella call Canon via Bridge (for auth), or directly (for performance)? | Medium | Open — for v1.0 single-server deployments, direct is fine; Bridge path needed for multi-server |
| Event schema versioning — should component events carry a version field for forward compatibility? | Low | Open |
| Cappella → Mosaic write failure recovery — should Cappella persist a retry queue? | High | Open — currently relies on operator-configured retries; more robust solution deferred |
