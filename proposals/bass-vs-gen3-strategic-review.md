# BASS vs. Gen3 — Strategic Review (2026-06-16)

**Question:** Is BASS too close a match to Gen3 (in audience, capabilities, strategy) to justify
continued investment, vs. adopting/extending Gen3 or a hybrid? Asked honestly, willing to
abandon, sunk-cost explicitly disallowed as a reason.

**Method:** an adversarial multi-agent panel with clean context (none invested in BASS): 5
independent lenses (abandon-prosecutor, continue-defender, neutral dimensional analyst, Gen3
reality-check *with live web + repo research*, third-path strategist) → 2 devil's-advocate
cross-examinations (one attacking each direction) → 1 synthesis. The research agents read the
actual repo (corrections below) and primary Gen3 sources.

## Verdict: **narrow hybrid** (high confidence on structure, medium on the Aperture endpoint)

"Abandon BASS?" is the wrong unit of analysis. BASS is two assets with opposite profiles, and
the evidence splits them cleanly:

1. **KEEP Hippo — low-regret, near-zero doubt.** Built, tested, in production at the brain bank,
   generic LinkML runtime, metadata-only, PROV-O provenance. Gen3 cannot replace it without a
   *worse-fitting, heavier* re-platform (per-node JSON-Schema re-modeling + standing up
   Sheepdog/Peregrine/Indexd + an object store), and Gen3 has **no documented metadata-only,
   single-lab, or LinkML-interop deployment**. Hippo's LinkML schema + SDK are portable even if
   the platform thesis is later dropped. Abandoning Hippo is the one genuinely wasteful move.

2. **DO NOT adopt Gen3 wholesale — verified disqualifying for this lab.** Gen3 mandates
   Kubernetes + Postgres + Elasticsearch + object store + a dozen+ microservices, is engineered
   for national federated commons run by dedicated DevOps, and has a **thin self-host community
   (~4–30 GitHub stars)**. The "adopt to offload maintenance" premise is **falsified**: a
   bus-factor-of-one team would be operationally *alone* on a heavier, worse-fitting stack it
   didn't write. Gen3's Guppy/Tube aggregation tier solves a *national-scale* problem the lab
   (~300 donors, <100k records, single-user, SQLite) does not have.

3. **DO NOT build Aperture as specced — this is where the analysis pushes hardest against our
   own session.** Aperture is ~471 LOC of Python backend stubs with **zero frontend code**. All
   five "more ambitious" differentiators exist only in design docs; our *own* `prior-art.md`
   flags the three load-bearing ones (derived binding, capability-scoped Worker client,
   agent-editable config) as **zero verified prior art / unproven / "carries real design
   risk."** Four of five (generic-over-any-backend, sandboxed view-descriptions,
   capability-negotiated adapter, agent-editable config) buy **optionality a single-deployment
   lab will never exercise.** This is where sunk-cost momentum is strongest and delivered value
   is weakest.

4. **THE SYNTHESIS — continue as a narrow hybrid:** Keep & finish Hippo. Close the real-but-small
   facet/count gap the **cheap way** — Hippo `order_by` + `totalCount` + client-side/DuckDB-WASM
   aggregation (the design's own option (c), viable at <100k). Build a **thin, bespoke React
   explorer over Hippo** (table + facets + count + export) using **Gen3's `explorerConfig` as the
   config template** — weeks, one person — *instead of* the novel sandboxed/agent runtime. Treat
   Gen3 strictly as a **design oracle**: steal the two-tier graph+index pattern (shelved until
   scale demands it), `manifestMapping` for cohort→file export, and tiered min-count privacy for
   Bridge. **Gate any further Aperture-runtime investment behind de-risking probes.**

   This deliberately **abandons the Aperture platform *thesis*** while keeping the one built
   asset and lifting Gen3's proven patterns. It is closer to the abandon-case's spirit than to
   "continue as designed."

## Decision matrix (synthesis)

| Dimension | Gen3 | BASS | Edge |
|---|---|---|---|
| Audience fit | National federated commons | One brain bank, ~300 donors, local | **BASS** |
| Built half (overlap) | Domain-locked per-node JSON-Schema metadata | Hippo: generic LinkML, metadata-only, PROV-O | **BASS** |
| Unbuilt half (overlap) | Data Explorer + Guppy/Tube, proven across commons | Aperture: stubs, zero frontend | **Gen3** |
| Aggregation/facet-count gap | Solved at national scale | None yet — but at <100k it's SQL/DuckDB, not a tier | tie |
| Strategy / positioning | Off-the-shelf commons; gitops+redeploy | SDK-first, config-as-data, agent-native (unproven) | tie |
| Operational cost (small team) | K8s + dozen microservices, needs DevOps | `hippo serve`, SQLite, no Docker | **BASS** |
| Extensibility / new viz | Config explorer, but new viz = React in-tree | Sandboxed view-descriptions — elegant but unbuilt | tie |
| Maintenance / longevity | Funded center, thin self-host community | Bus-factor-of-one, small surface, salvageable | tie |
| Build-it-yourself cost | Exists, but adopting = re-platform | Hippo cheap-kept; Aperture runtime is the risky remainder | tie |
| Sunk cost (honest) | neutral | Built part is the cheap Gen3-equivalent; unbuilt part is where momentum ≠ value | **Gen3** |

## Honesty corrections the adversarial process produced

- **Test count was inflated.** The continue-case cited "1321 test files / 634 tests"; ~1190 are
  vendored `.venv` files. First-party Hippo tests are **~131–146**. Hippo is real and tested —
  just not at the claimed scale.
- **The capability gap is real but its weight was inflated by a scale category-error.** At ~300
  donors / <100k records, facet counts + sort are a `GROUP BY`/`ORDER BY` or DuckDB-WASM — *not*
  a missing platform tier. Gen3's Guppy/Tube exists for national-scale aggregation the lab
  doesn't have. `order_by`/`totalCount` are days of Hippo work, not a multi-year subsystem.
- **"Adopt Gen3 to offload maintenance" is falsified** by the research (thin community, K8s
  mandate, no metadata-only/brain-bank/LinkML story): adoption *relocates* the maintenance
  burden onto a heavier, worse-fitting stack rather than reducing it.
- **The architectural convergence (fence+arborist≈Bridge, dictionary≈LinkML, Peregrine≈Hippo
  GraphQL) is ambiguous, not pro-BASS.** It validates the *patterns* (→ steal them); BASS differs
  at the *substrate* (LinkML-native, introspection-derived binding, provenance-by-construction).
  It argues for "steal patterns," not "adopt the deployment" — and not for "re-derive every
  service solo" either.

## Cruxes — these are the user's to answer (analysis can't)

1. **Is the real deliverable just a faceted explorer over donor/sample/datafile metadata?** If
   yes (core-loop.md implies it), Aperture's novel runtime is over-engineering.
2. **Do Aperture's three keystone bets prototype out?** The `hippoSchema` introspection resolver
   exists (`resolvers.py:679`) but has **zero consumers**; the Worker sandbox and the ADR-0010
   KM-curve probe are unbuilt. Until a spike exists, the differentiation is a hypothesis.
3. **Is multi-institution federation / NIH-commons membership / dbGaP-PFB interop on the 2–3 year
   horizon?** *The single cleanest flip-to-Gen3 condition.* The stated single-VA-brain-bank
   profile says no — but only the user knows.
4. **Is the `proposals/biodms2026` research/publication thesis real and resourced?** It's the
   only thing justifying the custom substrate beyond operational need — and even then it scopes
   to a *Hippo* paper, not building Aperture/Bridge/Cappella.
5. **Will the team ever exceed bus-factor-of-one?** Every longevity argument hinges on it.

## Conditions that FLIP to abandon/adopt-Gen3
- Federation / large cohorts / IRB-gated tiered access / dbGaP-PFB interop becomes a real
  near-term requirement (Gen3's domain-lock becomes an asset).
- A hands-on trial proves Gen3 can run genuinely slim (single-node, no K8s/ES) for metadata-only.
- All three Aperture keystone bets fail their probes *and* even a thin Hippo explorer proves hard
  (→ a configured Gen3 explorer or LabKey/REDCap/Gen3-MDS beats finishing a custom platform).
- biodms2026 is confirmed unresourced *and* Hippo's substrate bets prove covered by prior art
  (DataHarmonizer, Datomic/XTDB).

## Conditions that FLIP to continue (full Aperture)
- Deliverable stays a single-lab metadata explorer at Tier-1 scale (matches current profile).
- The introspection→derived-binding spike and Worker sandbox prototype out at acceptable effort.
- The cheap facet-gap path (order_by/totalCount + DuckDB-WASM) closes the gap in weeks.
- The team needs frequent non-developer / LLM-driven schema/portal changes Gen3's
  gitops+redeploy serves poorly (config-as-live-data becomes load-bearing).

## Recommended next actions
1. **Keep Hippo as-is** (not in dispute; don't re-platform the metadata layer).
2. **Run two time-boxed de-risking spikes (~1–2 wks each)** — the ones our own `prior-art.md`
   names: (a) wire a consumer of Hippo's `hippoSchema` resolver into a derived UI binding; (b) a
   minimal capability-scoped Web-Worker component emitting a validated view-description. **These
   gate all further Aperture-runtime investment.**
3. **Close the facet gap the cheap way now:** Hippo `order_by` + `totalCount`; prototype facet
   counts via DuckDB-WASM. Verify it covers the core-loop prefab before any index-tier work.
4. **Build a thin bespoke React explorer over Hippo** using Gen3's `explorerConfig` as the config
   template — ship the brain bank its headline feature first.
5. **Treat Gen3 as a design oracle only** (explorerConfig schema; two-tier index pattern shelved
   until scale; manifestMapping; min-count privacy). Do not stand up the Gen3 stack.
6. **Force a decision on biodms2026** (resourced research, or drop it from the platform
   justification). If real, scope to a Hippo-LinkML-runtime paper.
7. **One-day Gen3 minimal-standup trial** to settle the highest-leverage unknown: can it run slim
   for metadata-only? The answer moves the abandon/continue boundary.
8. **Defer/descope** Aperture's generic-over-any-backend, capability-negotiated adapter, and
   agent-editable-config pillars until a second backend or a non-developer-edit requirement
   actually exists.

## Weighting (synthesis, explicit)
~70% "keep Hippo + thin bespoke explorer + steal Gen3 patterns"; ~20% fuller Gen3 hybrid *if* a
lightweight Gen3 mode proves real or federation arrives; ~10% continue the full Aperture vision
— *defensible only if biodms2026 is genuinely resourced.* High confidence on the **structure**
(keep Hippo; don't adopt Gen3 wholesale; don't build Aperture as specced; steal patterns), medium
on the exact Aperture endpoint, which the probes + the federation/research cruxes resolve.
