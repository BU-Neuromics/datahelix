# DataHelix 1.0 — Six-Month Design-Sprint Roadmap

**Status:** Working roadmap (design-sprint output, 2026-07-07)
**Horizon:** 2026-07-07 → 2027-01-05 (26 weeks, four ~6-week phases)
**Scope decisions (ratified with maintainer, 2026-07-07):**
1. **Bridge minimal ships in 1.0** — 1.0 is a multi-user release; Bridge is the sole enforcing PEP/PDP (`sec6_security_model.md`, drylims#27, hippo#54).
2. **AI ambition = portal-complete + MCP agent surface** (Aperture ADR-0021's agent-first path). Data stories (Aperture ADR-0022–0025) and in-app chat stay deferred past 1.0.
3. **Cappella ships ONE reference adapter** proving live ingestion end-to-end; the full adapter catalog is 1.x.

This roadmap supersedes the milestone framing in `FABLE_HANDOFF.md` §6 where they
conflict, and maps back to it (M2→P2, M4→P2/P3, M5→P3 scoped to one adapter,
M6→P4). It is written for **handoff to agents**: every epic names its repo, size,
dependencies, and acceptance criteria. The **certified-frontier ledger**
(platform ADR-0001, `certification/`) is the release train — every phase ends in
a certified composition, and 1.0 itself is a ledger entry.

> **Way of working (all agents):** hippo uses the OpenSpec pipeline
> (spec → change → tasks → code+tests); aperture is ADR-first (decision before
> code; `design/INDEX.md` Decision Log is the source of truth); drylims records
> cross-component decisions in `platform/design/decisions/`. Contract files in
> `tests/contracts/` are load-bearing. One release = one bump PR (never batch).
> Escalate to humans: deploys touching PHI, open design questions marked
> **[HUMAN]** below, and anything that would break a certified pair.

---

## 0. Where we are (survey findings, 2026-07-07)

| Component | Spec | Code | Key fact |
|---|---|---|---|
| **Hippo** v0.10.1 | sec1–sec11 drafted (sec10/11 pending promotion) | mature, high velocity (~1 minor/2wks) | Wave-1 LinkML-core OpenSpec cluster untracked-vs-shipped; Postgres lags SQLite (xref/multivalued/polymorphic); **no tags, no release pipeline**; auth designed (sec8) but only pass-through in code |
| **Aperture** | 33 ADRs; design complete | MVP phases 0–4 merged (PRs #10–#14) | **Verified against a stub only** — #15 (live `hippo serve` integration) is the v1.0 gate and the linchpin for #16/#17/#19 |
| **Canon** | v0.2-draft complete | mid-v0.2; storage adapters + dynamic rules landed | Two OpenSpec changes nearly done (25/3, 16/5 tasks) |
| **Cappella** | v0.1 complete (v0.2 undesigned) | v0.1 code-complete, 27/27 features | No concrete external adapter; reactive triggers unbuilt |
| **Bridge** | sec1–sec6 v0.1 complete | **zero code** | Now the platform's sole PEP/PDP; PDP engine + Hippo `IN`-filter are tracked open work |
| **Platform** | ADR-0001 certification infra merged (PR #33) | ledger tooling live, boots are no-ops until artifacts publish | **Cross-component contract/platform CI disabled since 2026-06-17** — guardrail off |

**The two structural unlocks everything else waits on:**
1. **Aperture #15** (live integration) — validates four assumed GraphQL seams; unblocks #16 (contract file), #17 (control-plane recipe), #19 (write-loop).
2. **Hippo release engineering** — tags + PyPI + digest-addressed images. Until artifacts exist, the certified-frontier ledger idles and no composed pair is deployable evidence.

---

## 1. Phase plan

### Phase 1 — "Make it real" (wks 1–6, Jul 7 → Aug 17)
*Theme: replace assumptions with a live, certified composition. End-state: **the ledger's first real entry.***

| Epic | Repo | Size | Depends on | Acceptance |
|---|---|---|---|---|
| **P1.1 Hippo release pipeline** — tag convention, PyPI publish workflow, Docker build+push with digest; retro-tag v0.10.x | hippo | M | — | `vX.Y.Z` tag → published wheel + `ghcr.io/bu-neuromics/hippo@sha256:…`; digest lands in a release asset the drylims bump bot can read |
| **P1.2 Wave-1 LinkML-core reconciliation** — reconcile the five 0/N OpenSpec changes (`hippo-core-schema`, `id-registry`, `process-class`, `provenance-as-linkml-class`, + `hippo-ext-vocabulary`) against shipped code; finish real gaps (the `hippo_core.yaml` "placeholder" note); archive the 3 complete + finish the 5 near-complete changes | hippo | M | — | OpenSpec tracking matches reality; `hippo_core` slot inventory final; `schema_version=""` provenance fallback fixed |
| **P1.3 Aperture #15 — live `hippo serve` integration** — confirm/adjust the four seams (introspection enrichment, filter SDL, batch UoW incl. partial-set dry-run, structured ValidationResult) + `entityHistory`, CORS | aperture | M | seeded hippo (P1.5 fixture) | verify-skill drives pass against live hippo; seam module headers updated; ONBOARDING checklist cleared |
| **P1.4 Aperture artifact** — Dockerfile (static SPA + runtime endpoint injection or documented build-args), CI build+push with digest; version tagging | aperture | S/M | — | `ghcr.io/bu-neuromics/aperture@sha256:…` published per release |
| **P1.5 Control-plane recipe (aperture#17)** — `ApertureDocument` recipe via `recipe_import`; drylims bootstrap fixture consumes it (replacing the interim copy in `certification/fixtures/`) | aperture | S/M | P1.3 | footer reports LinkML-on-Hippo store on a stock seeded hippo; drylims fixture imports the recipe, not a fork of it |
| **P1.6 First certified pair** — fill `composition.lock.json` digests; certify workflow runs a real boot; fix golden-path suite against reality (e.g. `batchPut` vs `ingestBatch` naming, filter SDL) | drylims | M | P1.1, P1.3, P1.4 | `certified/aperture-*+hippo-*` tag exists with `result: pass`; deploy gate admits the pair |
| **P1.7 Re-enable contract CI (slice 1)** — restore `tests/contracts/` per-component for the stable seams (canon↔hippo, cappella↔hippo); prune stale assertions | drylims | M | — | contract jobs green and required on PRs; disabled-job comment in `tests.yml` retired |
| **P1.8 Canon v0.2 close-out** — finish `storage-adapter-plugin-system` (3 tasks) + `https-adapter-and-fetch-rules` (5 tasks); archive | drylims/canon | S | — | REUSE/FETCH/BUILD all live; suites green |
| **P1.9 Aperture #18 nav overrides** (unblocked, parallel) — `config/nav` document: derive-all + reorder/relabel/hide + default landing; hide control-plane collection | aperture | M | — | per issue #18 acceptance |

**[HUMAN] decisions due in P1:** platform name settled as DataHelix (1.0 branding/docs follow); confirm `ghcr.io` as registry + digest/attestation format (ADR-0001 open note).

### Phase 2 — "Contract-guarded and portal-complete" (wks 7–13, Aug 17 → Oct 5)
*Theme: seams under contract; the portal reaches feature-complete; storage/API converge on freezable. Maps to FABLE M2 + M4 (part).*

| Epic | Repo | Size | Depends on | Acceptance |
|---|---|---|---|---|
| **P2.1 Aperture→Hippo contract file (aperture#16)** — portable introspection assertions + golden pairs; hippo CI job runs it against booted `hippo serve`; aperture CI runs it against its stub; drylims fixture consumes it | aperture + hippo + drylims | M | P1.3 | a hippo PR breaking a seam fails hippo CI; contract versioned; ledger entries record contract version via the fixture |
| **P2.2 Hippo #96 — aggregation primitive (X1)** — `order_by`, `totalCount`, facet counts, range filters; SDK-first, REST+GraphQL parity | hippo | L | P1.2 | GraphQL list surface advertises all four; SQLite+Postgres tests |
| **P2.3 Aperture #20 — light up X1 capabilities** — sort, counts, "N of M" pager, range facets, OR multi-select | aperture | M | P2.2 | features appear via pure capability negotiation; nothing changes against an old hippo |
| **P2.4 Aperture #19 — write-loop completeness** — availability/supersede affordances, field clearing (null semantics), saved-view removal UI | aperture | M | P1.3 | per issue #19 acceptance |
| **P2.5 Hippo Postgres parity** — per-class-table migration; xref reverse lookup, multivalued refs (ADR-0002), polymorphic ingest (ADR-0003); ratify both ADRs; publish parity matrix | hippo | L | P1.2 | `hippo.yaml` backend swap is truthful for all shipped features; ADR-0002/0003 Accepted |
| **P2.6 Unified ingestion framework** (BREAKING, pre-freeze) — `EntityLoader` ABC lands in hippo; Cappella's `adopt-hippo-loaders` change executes; cyclic-FK ingest (hippo#95) + ingest `--db-path` (hippo#89) fixed en route | hippo + drylims/cappella | L | P1.2 | one ingest path; `test_entity_loader_contract.py` re-enabled and green; breaking change lands before any API freeze |
| **P2.7 Hippo transport v0.5 slice** — REST `PUT`, bulk availability, OR filters, cursor pagination + GraphQL parity, exception→HTTP map (#62), DRS router mount (#55), status introspection (#61), `query_updated_since` (#63, needed by Cappella poll triggers) | hippo | M/L | P1.2 | INDEX "Planned v0.5 Phase 1" items closed; GraphQL known-limitations list shrinks accordingly |
| **P2.8 Bridge v0.1 skeleton** — from zero: `/api/v1/{component}/` routing, API-key auth, `X-DataHelix-Actor`/`X-DataHelix-Roles` injection, trust-proxy CIDR, health aggregation; openplan decomposition first | drylims/bridge | L | — (parallel track) | authenticated REST proxying to hippo works in compose; Bridge has its own test suite + CI job |
| **P2.9 Hippo `IN`-filter** — set-membership filter (predicate-pushdown prerequisite, sec6 §6.8) | hippo | S/M | — | `IN` composes with equality/AND/OR on REST+GraphQL |

**[HUMAN] decision due in P2:** which hippo schema-sync slices (503-on-mismatch / polling reload / expand-contract) are 1.0-blocking vs 1.x.

### Phase 3 — "Multi-user + the agent surface" (wks 14–20, Oct 5 → Nov 23)
*Theme: the two headline 1.0 features. Maps to FABLE M4 (rest) + M5 (scoped).*

| Epic | Repo | Size | Depends on | Acceptance |
|---|---|---|---|---|
| **P3.1 Bridge as sole PEP incl. GraphQL** (drylims#27) — GraphQL operation parsing, RBAC matrix solely in Bridge, PDP engine (predicates + field masks), capability-scoped enforcing client | drylims/bridge | L | P2.8, P2.9 | role-scoped user sees predicate-filtered, field-masked results through the same autogenerated GraphQL contract; graceful degradation per sec6 §6.5 |
| **P3.2 Hippo #54 — strip auth logic** — delete `require_auth`/`require_graphql_auth`; keep pass-through actor middleware; amend sec8.3 (no RBAC in `BridgeAuthMiddleware`) | hippo | S | P3.1 header contract stable | hippo holds zero authn/authz; actor is provenance metadata only |
| **P3.3 Aperture on Bridge** — swap no-op `scopedClient` for the enforcing client; two-credential model surfaces; honest degradation for masked fields | aperture | M | P3.1 | same SPA build works direct-to-hippo (local) and through Bridge (multi-user); Playwright multi-user scenario added to certification nightly tier |
| **P3.4 Aperture MCP agent surface** — ratify ADR-0018 (user-delegated authority) + ADR-0021 scope; new ADR for the MCP server design; implement: an MCP server exposing the domain graph (browse/query, staged workflow ops incl. dry-run, saved views/config-as-data) with the same capability-scoped client as the SPA | aperture | L | P1.3; P3.1 for multi-user mode | a coding agent connected via MCP can: query collections, stage+dry-run+commit a batch workflow, and read/write control-plane documents — all appearing in provenance under the invoking user's actor |
| **P3.5 Agentic keystone probe (rung 1)** — the vision's decisive test: an agent edits portal config-as-data (nav/workflow config) → dry-run validates → applies; record outcome as an ADR/status report | aperture | S/M | P3.4 | probe result documented; go/no-go input for post-1.0 agentic roadmap |
| **P3.6 Cappella reference adapter** — design (v0.2 design doc first: adapter choice **[HUMAN]** — REDCap vs CSV-batch drop), then implement ONE production adapter + `hippo_poll`/webhook trigger + `SyncRun` audit trail, on the unified `EntityLoader` | drylims/cappella | L | P2.6, P2.7 (`query_updated_since`) | live source → Cappella → hippo ingestion runs on a schedule with idempotent re-runs and a queryable audit trail |
| **P3.7 DRS + AI-readiness slice** — `drs-self-uri` decomposed + implemented in hippo; Canon FETCH-via-DRS wired | hippo + drylims/canon | M | P2.7 (DRS mount) | `drs://host/uuid` resolves; Canon fetch path exercises it in a platform test |

### Phase 4 — "Freeze, harden, ship" (wks 21–26, Nov 23 → Jan 5)
*Theme: 1.0 as evidence, not a version string. Maps to FABLE M6.*

| Epic | Repo | Size | Depends on | Acceptance |
|---|---|---|---|---|
| **P4.1 API freeze + 1.0 cuts** — hippo 1.0.0, aperture 1.0.0: semver commitment docs, deprecation policy, LinkML pin-tracking release note discipline | hippo, aperture | M | P2.5–P2.7, P3.* | breaking-change budget spent; freeze documented; both artifacts published by digest |
| **P4.2 The 1.0 certified composition** — bump PRs → golden path green → `certified/aperture-1.0.0+hippo-1.0.0`; cut `release/lts-1` maintenance branches per ADR-0001 (frontier + 1 LTS policy starts) | drylims | S/M | P4.1 | ledger entry exists; deploy gate admits exactly this pair; LTS branch carries frozen suite+fixture |
| **P4.3 Deployable stack (M6 DoD)** — `docker compose up` (hippo+aperture+bridge+postgres) from docs alone: fresh clone → deploy → ingest via Cappella adapter → browse/write/workflow in portal → agent connects over MCP; deploy gate wired in | drylims | M | P3.*, P4.2 | a documented cold-start run-through completes with no undocumented steps (the M6 "docs alone" test, executed by an agent that has never seen the repo) |
| **P4.4 NFR benchmark harness** — implement sec7 measurement (p99 targets, ingest throughput); publish `platform/benchmarks/baseline.md`; certification nightly gains the regression gate (sec5 §5.8) | hippo + drylims | M | P4.1 | baseline published; nightly regression thresholds active |
| **P4.5 Docs 1.0** — mkdocs `--strict` restored; sec6/domain-graph in nav; per-component 1.0 guides; Postgres parity matrix; rename fallout if **[HUMAN]** renames platform | drylims | M | P4.1 | strict build green; getting-started verified by the P4.3 cold-start |
| **P4.6 Hygiene close-out** — ADR statuses ratified across repos; stale docs fixed (hippo CLAUDE.md sec status; aperture implementation-plan header); vestigial aperture PYTHONPATH entries removed; small-issue sweep (hippo #55/#56/#57/#61/#70/#78/#89 leftovers) | all | S/M | — | zero known doc-vs-reality contradictions at 1.0 |

---

## 2. Cross-repo dependency spine (critical path)

```
hippo P1.1 release pipeline ──────────────┐
hippo P1.2 LinkML-core reconcile ──┐      ├─► P1.6 first certified pair ─► P2.1 contract file
aperture P1.3 live integration ────┤      │
aperture P1.4 artifact ────────────┘      │
                                          ▼
hippo P2.2 X1 aggregation ─► aperture P2.3 light-up
hippo P2.5 Postgres parity ─► P4.1 freeze
hippo P2.6 unified ingestion ─► cappella P3.6 reference adapter
hippo P2.9 IN-filter ─► bridge P3.1 PDP ─► hippo P3.2 strip auth ─► aperture P3.3 on-Bridge
aperture P3.4 MCP surface ─► P3.5 keystone probe
ALL ─► P4.1 freeze ─► P4.2 certified 1.0 ─► P4.3 deployable stack
```

Single points of failure: **P1.3** (if a seam assumption is badly wrong, Phase-1
re-planning) and **P3.1** (Bridge from zero; the PDP engine spike should run in
P2 to de-risk). Both have early-warning probes scheduled in the phase before
their dependents.

## 3. Explicit non-goals for 1.0 (deferred, with pointers)

- **Data stories / instruction paths** (Aperture ADR-0022–0025) and **in-app chat** (ADR-0021 reversal) — post-1.0; the MCP surface + keystone probe is the 1.0 beachhead.
- **Embedded schema editor** (aperture#2; hippo X3a/X3b) — post-1.0.
- **View-description vocabulary chain** (Aperture ADR-0010→0013 keystone probes) — schedule the ADR-0010 survival-curve probe opportunistically; not gating.
- **linkml-store adoption (Option α)** (hippo#2–#5) — explicitly "blocked on internal v1.0 milestone"; revisit after.
- **Full adapter catalog (STARLIMS/HALO), federation, OAuth/OIDC RBAC, Neo4j/DynamoDB backends, workflow executors beyond cwltool** — 1.x.
- **Efficient federated bulk-slice extraction** (domain-graph.md's "hardest thing") — correctly deferred.

## 4. Handoff protocol (for the agents executing this)

1. **One epic = one agent engagement**, on a feature branch in the owning repo; PR per epic (or per increment for L epics). Follow the owning repo's process (hippo: OpenSpec change first; aperture: ADR first when a decision is embedded; drylims: platform ADR for cross-component decisions).
2. **Never break a certified pair:** changes to a seam require the contract file (post-P2.1) green in your own CI before release; releases are one-per-bump-PR into drylims.
3. **Acceptance criteria above are the definition of done** — an epic isn't done until its acceptance row is demonstrably true (tests/CI/certification evidence, not assertion).
4. **Escalate [HUMAN] items** — never resolve them by implication. Current queue: platform name; registry/attestation choice; schema-sync 1.0 scope; Cappella adapter choice (REDCap vs CSV-batch).
5. **Status legibility:** update the owning repo's `design/INDEX.md` (and this file's phase tables via PR) as epics complete; the drylims Dependency Dashboard + ledger tags are the ground truth for composition state.

## 5. Six-month success definition

1.0 exists when, from documentation alone, a fresh agent can: stand up the
composed stack with `docker compose up`; ingest a live source through the
Cappella reference adapter; browse, filter (with counts/sort), write, and run an
atomic multi-entity workflow in the portal as an authenticated user whose access
Bridge visibly scopes; connect a coding agent over MCP and have it perform a
dry-run-validated config change under that user's authority; and verify all of
it is provenance-tracked, benchmarked against published NFR baselines, and
recorded as `certified/aperture-1.0.0+hippo-1.0.0` in the ledger that gates the
deployment it just performed.
