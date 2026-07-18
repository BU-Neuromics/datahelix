# DataHelix Platform — Performance Baseline Targets

**Status:** Draft v0.1
**Last updated:** 2026-03-31
**Source specs:** `mosaic/design/sec7_nfr.md`, `canon/design/sec7_nfr.md`, `cappella/design/sec6_nfr.md`

This document collates the non-functional performance targets from all three core components into a single platform-level reference. These are the targets against which Phase 1 benchmarking results will be evaluated.

---

## Workload Profiles

All targets below are stated against these reference workload profiles. Choose the tier that matches your deployment.

| Tier | Entity count | Concurrent users | Write rate | Notes |
|---|---|---|---|---|
| **Tier 1** (laptop / workstation) | < 100k | 1 | < 10 writes/min | SQLite, single process |
| **Tier 2** (lab server) | 100k–2M | 2–10 | < 100 writes/min | SQLite or PostgreSQL |
| **Tier 3** (cloud / HPC) | 2M+ | 10+ | adapter-dependent | PostgreSQL; Cappella async |

Phase 1 targets Tier 1 and Tier 2. Tier 3 is out of scope for Phase 1 benchmarking.

---

## Mosaic — Storage & Query (SQLite adapter, Tier 1/2)

Source: `mosaic/design/sec7_nfr.md §7.1`

| Operation | Target (p99) | Notes |
|---|---|---|
| Single entity read (`client.get`) | < 5ms | Indexed UUID lookup |
| Filtered query (100 results) | < 50ms | With partial index on filter field |
| Single entity write (`client.put`) | < 20ms | Includes schema validation + provenance write |
| Batch ingest (1,000 entities) | < 30s | ~30ms/entity including validation |
| Fuzzy search (FTS5, 10 results) | < 100ms | SQLite FTS5; field must have `search: fts` |
| `query_updated_since` (500 entities) | < 200ms | Via `entity_provenance_summary` view |
| `client.history` (100 events) | < 50ms | Indexed by `entity_id` |
| `PUT /entities/{type}/{id}` (explicit update) | < 25ms | Includes existence check + validation (v0.5 target) |
| `POST /entities/{type}/bulk-availability` (1,000 records) | < 60s | ~60ms/record; 207 on partial success (v0.5 target) |
| Cursor-paginated list (page of 100) | < 50ms | Stateless cursor; additive to offset mode (v0.5 target) |
| OR-filter query (multi-value, 100 results) | < 75ms | Same-field OR via multi-value param (v0.5 target) |

**Anti-patterns that blow these targets:**
- N+1 provenance queries — use `entity_provenance_summary` view for batch reads
- Unbounded queries — always supply `limit`; SDK hard max is 10,000
- Unexpanded `ref` fields in CEL validators on large collections — cap `max_expand_list_size` (default: 200)

---

## Canon — Reproducibility & Resolution Latency

Source: `canon/design/sec7_nfr.md §7.1–7.2`

Canon's primary NFRs are qualitative (reproducibility, correctness, idempotency) rather than quantitative. The latency target is derived from the Cappella integration.

| Metric | Target | Notes |
|---|---|---|
| `resolve()` latency — REUSE path | < 1.5s | Mosaic query overhead only; no CWL invoked |
| `resolve()` latency — BUILD path overhead | ≤ CWL execution time + 500ms | Canon overhead is at most 500ms on top of actual execution |
| `canon plan` dry-run | < 2s | Mosaic queries for REUSE check; no execution |
| `canon status` query (20 recent runs) | < 500ms | Backed by indexed `WorkflowRun` Mosaic query |

**Correctness requirements (non-negotiable — not subject to version trade-offs):**
- Every field comparison in Mosaic queries is exact match — no fuzzy matching in `resolve()`
- `CanonResolutionError` on zero or multiple matches — never silently picks from many
- Tool version is always required in rules — no silent version resolution
- Unpropagated wildcard validation at startup prevents silent provenance loss
- All `WorkflowRun` entities include CWL file SHA256, runner version, and container image digest

---

## Cappella — Integration & Resolution Throughput

Source: `cappella/design/sec6_nfr.md §6.1`

| Metric | Target | Notes |
|---|---|---|
| Adapter sync throughput | ≥ 500 records/min | Batch adapter syncs; SQLite Mosaic backend |
| Resolution latency — all REUSE (≤10 samples) | ≤ 2s | Mosaic queries only; Canon not invoked |
| Resolution latency — BUILD path (≤10 samples) | ≤ Canon execution time + 500ms | Cappella overhead ≤ 500ms |
| Async resolution startup (`POST /resolve` → `202`) | ≤ 200ms | Returns `run_id` immediately |
| Health endpoint (`GET /health`) | ≤ 100ms | Cached adapter health check |
| Partial failure processing overhead | ≤ 100ms per unresolved sample | Cappella's exception handling, not Canon execution |

**Phase 1 target tier:** Tier 1 only (synchronous, single-process). Tier 2 async resolution (task queue, concurrent Canon calls) is deferred to v0.2.

---

## Cross-Component: Round-Trip Targets

These are the integrated targets for the full pipeline, derived from component targets above. They apply to the Phase 1 integration test suite regression gates (see `platform/design/sec5_integration_test_strategy.md §5.8`).

| Scenario | Target | Notes |
|---|---|---|
| Adapter sync: 1 new record to Mosaic | < 5s wall clock | Includes ExternalID lookup + Mosaic write |
| Canon resolve: REUSE, 1 sample | < 5s wall clock | Mosaic query + contract overhead |
| Canon resolve: BUILD, 1 sample (mock CWL) | < 15s wall clock | Mock CWL returns immediately; Canon + Mosaic provenance write |
| Full round-trip: 10 samples all REUSE | < 20s wall clock | Cappella resolution run against live Mosaic |
| Full round-trip: 10 samples all BUILD (mock CWL) | < 45s wall clock | Includes WorkflowRun + output entity writes per sample |

---

## How to Record Baselines

When Phase 1 benchmarking runs occur, record actual measurements in the table below. The columns are:
- **Date:** benchmark run date
- **Git ref:** commit hash or tag
- **Environment:** hardware tier (Tier 1/2/3) and OS
- **Actual p99:** measured value
- **Pass/Fail:** green if within target, red if outside

| Component | Operation | Date | Git ref | Environment | Actual p99 | Pass/Fail |
|---|---|---|---|---|---|---|
| Mosaic | `client.get` | — | — | — | — | — |
| Mosaic | Filtered query (100) | — | — | — | — | — |
| Mosaic | Single write | — | — | — | — | — |
| Mosaic | Batch ingest (1,000) | — | — | — | — | — |
| Canon | `resolve()` REUSE | — | — | — | — | — |
| Cappella | Adapter sync (500/min) | — | — | — | — | — |
| Cappella | Resolution (10 REUSE) | — | — | — | — | — |
| Platform | Round-trip (10 BUILD, mock CWL) | — | — | — | — | — |

Populate this table as benchmarks are run during Phase 1 (April–June 2026).
