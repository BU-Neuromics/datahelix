## 5. Cross-Component Sync

**Document status:** Draft v0.1
**Depends on:** sec2_architecture.md, Hippo sec5 (ingestion), Hippo sec6 (provenance), Cappella sec5 (workflows)
**Feeds into:** Bridge sec6 (NFR — sync latency targets), deployment docs

---

### 5.1 What Cross-Component Sync Addresses

BASS components operate independently. Each has its own state:

- **Hippo** stores entity metadata and provenance records.
- **Cappella** tracks pipeline run state, reconciliation records, and trigger history.
- **Canon** maintains a file artifact cache and resolution records.

After a pipeline run, a reconciliation scan, or a bulk ingest, these stores must be mutually
consistent. Inconsistencies arise in two ways:

1. **Write failures under partial completion** — A Cappella pipeline registers outputs to
   Hippo, but the Hippo write fails mid-batch. Cappella believes the run succeeded; Hippo has
   partial data.

2. **Eventual-consistency lag** — Components are written independently (SDK calls, direct
   REST) without a distributed transaction. A brief window exists where Cappella's run log
   shows success but Hippo's entity store has not yet reflected the output.

Bridge's sync subsystem provides **detection and repair** for both cases. It does not impose
a two-phase commit protocol — that would couple components too tightly. Instead, it uses
**reconciliation events** and **consistency checks** to identify and surface discrepancies.

---

### 5.2 Sync Model

Bridge uses an **event-driven consistency** model:

```
┌──────────┐  run_completed  ┌──────────────┐  check_hippo  ┌────────┐
│ Cappella │────────────────▶│ Bridge Sync  │──────────────▶│  Hippo │
│          │                 │  Engine      │               │        │
│          │◀────────────────│              │◀──────────────│        │
│          │  consistency_ok │              │  entities_ok  └────────┘
└──────────┘  (or mismatch   └──────────────┘
              event)
```

1. **Event subscription** — Cappella emits structured lifecycle events (run started, run
   completed, reconciliation finished). Bridge subscribes to these events via a lightweight
   in-process message bus (v0.1) or a persistent event queue (v1.1+).

2. **Consistency check** — On receipt of a completion event, Bridge queries both Cappella
   (what did the run produce?) and Hippo (are those entities present?) and compares.

3. **Mismatch handling** — If a discrepancy is found, Bridge emits a `sync_mismatch` event,
   records it in the sync event log, and optionally triggers a repair workflow.

---

### 5.3 Event Types

Bridge subscribes to and emits the following sync-relevant events:

#### 5.3.1 Inbound Events (from components)

| Event | Source | Payload |
|---|---|---|
| `cappella.run.completed` | Cappella | `run_id`, `pipeline_id`, `outputs: [{entity_type, external_id}]`, `actor` |
| `cappella.run.failed` | Cappella | `run_id`, `pipeline_id`, `error`, `partial_outputs` |
| `cappella.reconciliation.completed` | Cappella | `scan_id`, `discrepancy_count`, `resolved_count` |
| `hippo.ingest.batch_completed` | Hippo | `batch_id`, `entity_type`, `count`, `actor` |
| `canon.cache.evicted` | Canon | `artifact_ids: []`, `reason` |

#### 5.3.2 Outbound Events (from Bridge Sync Engine)

| Event | Consumers | Meaning |
|---|---|---|
| `bridge.sync.mismatch` | Observability, ops team | Cappella says entity exists; Hippo does not |
| `bridge.sync.repaired` | Observability | Mismatch resolved by re-trigger or manual correction |
| `bridge.sync.stale_cache` | Canon | Canon has artifacts for entities that no longer exist in Hippo |

---

### 5.4 Consistency Check Procedures

#### 5.4.1 Cappella → Hippo Post-Run Check

After receiving `cappella.run.completed`, Bridge performs:

1. Fetch `outputs` list from the completed run record: `GET /cappella/runs/{runId}/outputs`
2. For each output, verify entity existence in Hippo: `GET /hippo/entities/{type}/{externalId}`
3. If any entity is missing, record a `bridge.sync.mismatch` event with:
   - `run_id`, `missing_entities`, `actor`, `timestamp`
   - `repair_strategy`: `resubmit_run` | `manual` (from config)
4. If all entities are present, record `bridge.sync.ok`.

This check runs asynchronously and does not block the pipeline run response to the caller.

#### 5.4.2 Canon Cache Staleness Check

After a Hippo bulk deletion or availability change:

1. Bridge queries Canon for artifacts associated with the affected entities.
2. If Canon has cached artifacts for entities that are now unavailable, Bridge emits
   `bridge.sync.stale_cache` so Canon can evict those artifacts on its next sweep.

#### 5.4.3 Periodic Full Consistency Scan

Bridge can run a scheduled full consistency scan (configurable interval, default: daily):

- Compare Cappella's run output history with Hippo's entity provenance.
- Surface runs that produced outputs not present in Hippo.
- Surface Hippo entities whose provenance references Cappella runs that no longer exist.

Scan results are written to the sync event log and available via:
`GET /api/v1/bridge/sync/scan/latest`

---

### 5.5 Mismatch Repair

Bridge does not automatically repair all mismatches — some require human judgement. The
repair strategy per mismatch type is configurable:

| Mismatch Type | Default Strategy | Options |
|---|---|---|
| Missing Hippo entity after Cappella run | `alert_only` | `alert_only`, `resubmit_run` |
| Stale Canon artifact | `evict_on_next_sweep` | `evict_immediately`, `evict_on_next_sweep`, `alert_only` |
| Partial Cappella output batch | `alert_only` | `alert_only`, `resubmit_run` |
| Cappella run referencing non-existent Hippo entity | `alert_only` | `alert_only` |

`resubmit_run`: Bridge calls `POST /cappella/runs` with the same pipeline and inputs as the
failed run. This is safe only for idempotent pipelines (those that use ExternalID upsert
semantics in Hippo). Bridge checks idempotency metadata on the pipeline definition before
auto-resubmitting.

---

### 5.6 Sync Event Log

All sync events are stored in Bridge's local sync event log (SQLite or PostgreSQL table).

Schema:

```
sync_events
├── id           UUID PRIMARY KEY
├── event_type   TEXT  (e.g. 'bridge.sync.mismatch')
├── source       TEXT  (component emitting the triggering event)
├── source_id    TEXT  (e.g. run_id, batch_id)
├── actor        TEXT
├── details      JSON
├── resolved     BOOLEAN DEFAULT false
├── resolved_at  TIMESTAMP
├── created_at   TIMESTAMP
```

Query API:

```
GET /api/v1/bridge/sync/events?status=unresolved&limit=50
GET /api/v1/bridge/sync/events/{eventId}
POST /api/v1/bridge/sync/events/{eventId}/resolve   (admin only)
GET /api/v1/bridge/sync/scan/latest
POST /api/v1/bridge/sync/scan                       (trigger on-demand scan; admin only)
```

---

### 5.7 Event Transport

#### v0.1: In-Process Event Bus

For v0.1 (single-server deployments), events are dispatched in-process using a simple
asyncio-based pub/sub bus:

```python
# bridge/sync/event_bus.py
bus = EventBus()
bus.subscribe("cappella.run.completed", sync_engine.on_run_completed)
bus.emit("cappella.run.completed", payload)
```

Events are not persisted in the bus. If Bridge restarts mid-check, the check is lost. This
is acceptable for v0.1; missed checks are caught by the next periodic scan.

#### v1.1: Persistent Event Queue

For production deployments where Bridge may restart during a long-running check, v1.1 will
introduce an optional persistent event queue backend (Redis Streams or PostgreSQL LISTEN/NOTIFY).
This is explicitly out of scope for v0.1.

---

### 5.8 Open Questions

| Question | Priority | Status |
|---|---|---|
| Should auto-resubmit (`resubmit_run`) require an approval step for non-idempotent pipelines? | High | Open |
| How should Bridge handle sync checks when a component is temporarily unreachable (retry vs. skip)? | High | Open — likely exponential backoff with a max-retry cap |
| Should sync mismatches be surfaced in the Aperture web portal as alerts? | Medium | Deferred to Aperture v0.2 |
| Event schema versioning — should events carry a schema version for forward compatibility? | Low | Open |
