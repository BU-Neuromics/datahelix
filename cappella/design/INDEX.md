# Cappella — Integration & Harmonization Engine
## Specification Index

**Codename:** Cappella  
**Component:** Integration & Harmonization Engine  
**Version:** 0.1-draft (design in progress)

---

## Document Map

| File | Section | Status | Notes |
|---|---|---|---|
| `sec1_overview.md` | 1. Overview & Scope | ⬜ Not started | Conductor/integration engine role, stateless design, Hippo as sole backend |
| `sec2_architecture.md` | 2. Architecture | ⬜ Not started | Trigger engine, adapter registry, action dispatcher, internal event bus |
| `sec3_adapters.md` | 3. Adapter System | ⬜ Not started | ExternalSourceAdapter implementations, field mapping config, transformation pipeline |
| `sec4_audit.md` | 4. Audit & Observability | ⬜ Not started | Structured run logs (MVP), future SyncRun entities in Hippo |
| `sec5_workflows.md` | 5. Workflow Execution | ⬜ Not started | Workflow executor strategy, Nextflow/Snakemake integration, output ingestion |
| `sec6_nfr.md` | 6. Non-Functional Requirements | ⬜ Not started | |

---

## Key Decisions (from Platform Design Sessions)

See `platform/design/INDEX.md` for full rationale and config format examples.

| Decision | Choice |
|---|---|
| Primary role | Integration and harmonization engine — the "conductor" coordinating all data sources into Hippo |
| Storage | Stateless — Hippo is the sole persistent store; Cappella owns no data |
| Hippo dependency | Required — Cappella cannot function without a Hippo instance |
| External adapter implementations | Live in Cappella (STARLIMS, HALO, REDCap, partner portals) — `ExternalSourceAdapter` ABC stays in Hippo |
| Field mapping and transformation config | Lives in Cappella adapter config — separate from Hippo's canonical schema |
| Trigger model | Unified `source` + `action` format: `webhook`, `schedule`, `hippo_poll`, `manual`, `internal_event` |
| Action chaining | Actions emit named internal events (`emits:`); triggers subscribe with `type: internal_event` |
| Event payload | Entity IDs only — downstream actions query Hippo fresh at execution time |
| Query-fresh-at-invocation | All actions read current Hippo state at execution time; never rely on stale trigger context |
| Hippo reactive triggers (MVP) | Polling (`hippo_poll`) — sufficient because Cappella drives most Hippo writes in normal operation |
| Hippo reactive triggers (future) | Hippo event hook plugin system — deferred |
| Idempotency (MVP) | Upsert by ExternalID — look up by source system ID, update if changed, create if absent |
| Idempotency (future) | Short-window digest deduplication for webhook retries — deferred to when live integrations are scoped |
| Out-of-order delivery | Deferred — not in MVP scope |
| Operational audit (MVP) | Structured JSON logs per trigger execution (run_id, trigger, adapter, status, entity counts, errors) |
| Operational audit (future) | `SyncRun` entities in Hippo — log schema mirrors Hippo entity shape for easy migration |
| Conditional triggers | `when:` CEL condition on trigger source — same expression language as validators |
| Tooling | `cappella trigger explain <name>` — shows full trigger chain, subscriptions, conditions |
| Artifact resolution | Delegated entirely to Canon — Cappella calls `canon.resolve(entity_type, params)` for per-sample/per-artifact work; Canon handles REUSE/FETCH/BUILD/FAIL internally |
| Workflow execution | In scope for aggregate analyses only (multi-sample inputs) — Cappella invokes Canon's `CWLExecutorAdapter` directly and ingests via Canon's `OutputIngestionPipeline`. Single-artifact CWL execution is always Canon's responsibility. |
| Aggregate analysis (v0.1) | Cappella collects per-sample URIs from Canon, constructs multi-input CWL job, executes directly using Canon's executor adapter layer |
| Aggregate analysis (v0.3+) | Will be replaced by Canon aggregate rules — Cappella degrades to a thin orchestrator calling `canon.resolve()` for cohort-level entities too |
| Canon relationship | Canon is Cappella's artifact resolution engine, NOT an external data source adapter. It is structurally different from STARLIMS/REDCap adapters. |
| Workflow executor strategy | **Open** — wrap Nextflow/Snakemake vs. define own; see open questions |

---

## Open Questions

| Question | Priority | Notes |
|---|---|---|
| Workflow executor strategy | ~~High~~ **Resolved** | Canon owns per-artifact CWL execution. Cappella delegates artifact resolution to `canon.resolve()`. For v0.1 aggregate/cohort-level analyses (multi-sample inputs), Cappella invokes Canon's `CWLExecutorAdapter` directly and ingests results via `OutputIngestionPipeline`. Cappella does NOT wrap Nextflow/Snakemake — it reuses Canon's executor adapter layer. Aggregate Canon rules (v0.3) will eventually replace direct Cappella CWL execution. |
| Cappella adapter config format | High | Field mapping + transformation pipeline format not yet designed. Needs to express more than field-to-field mappings: vocabulary normalization, confidence thresholds, conditional transforms. |
| Idempotency for live synchronous integrations | High (deferred) | Full design when live integrations are scoped: webhook digest deduplication, out-of-order delivery, source timestamp handling. ExternalID upsert is the stable foundation. |
| Execution backend model | Medium | Local process vs. queue-backed worker vs. HPC submission. Must scale from laptop to cloud without code changes — consistent with Hippo's deployment tier model. |
| Trigger failure handling | Medium | Retry logic, dead-letter queue, alerting strategy for failed trigger executions. |

---

> ⚠️ The existing [Cappella user docs](../docs/introduction.md) predate this design session and describe a generic workflow executor. They should be rewritten after sec1 and sec2 are complete.
