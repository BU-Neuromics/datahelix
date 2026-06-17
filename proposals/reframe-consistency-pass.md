# Reframe Consistency Pass — Propagate the Domain-Graph / AI-Explorer Reframe

**Status:** 🟠 Open work list (created 2026-06-17). A documentation/organization consistency pass
across drylims + submodules to propagate the 2026-06-17 reframe. The reframe itself is **decided —
do not relitigate it**; this pass only makes the rest of the docs *consistent* with it.

## Read first (the canonical source of truth)

1. [`platform/design/domain-graph.md`](../platform/design/domain-graph.md) — the foundational data
   model (the reframe's anchor).
2. [`aperture/design/vision.md`](../aperture/design/vision.md) — Aperture as AI-native explorer.
3. [`aperture/design/prefab/data-stories.md`](../aperture/design/prefab/data-stories.md) — the MVP.
4. [`proposals/bass-vs-gen3-strategic-review.md`](./bass-vs-gen3-strategic-review.md) — the
   strategic verdict (narrow hybrid) the reframe answers.

## The reframe in one paragraph (the target the docs must reflect)

A BASS deployment is **one typed knowledge graph (the "domain graph")**: the LinkML schema is its
type system and **Hippo is the runtime that becomes it** ("LinkML runtime" and "domain graph" are
the same claim). Every query returns a **knowledge subgraph**. **"Metadata vs. data" is a
query-relative *role*, not a storage category** — so Hippo is **not** a "metadata store," it is the
**structured domain graph**. The real architectural line is **structured records (Hippo) vs. bulk
payloads (Canon/Cappella)**, the latter entering as induced subgraphs unioned at query time
(OBDA/VKG, deferred). **Aperture** is an **AI-native data & workflow explorer** over that graph —
the config-driven portal is its *substrate*, not the product.

## Cross-cutting terminology rules (apply everywhere)

- "metadata store / Metadata Tracking Service" → **"structured domain graph"** (Hippo).
- "config-driven data portal / metadata browser" (as the *product*) → **"AI-native data & workflow
  explorer"**; the portal is the *substrate*.
- Don't assert "metadata vs data" as a storage property — it's a query-relative role.

## Scope note — this spans repos

`hippo/` and `aperture/` are **submodules** (separate repos: BU-Neuromics/hippo,
BU-Neuromics/aperture). Edits there require a commit **in the submodule** + push, then a
**submodule-pin bump** committed in drylims (see root `CLAUDE.md` "Working with submodules").
`platform/`, `bridge/`, `proposals/`, and root docs are **in-tree** in drylims.

## Checklist

### 1. Hippo self-description — "metadata store" → "structured domain graph"  *(hippo submodule)*
- [ ] `hippo/CLAUDE.md` — "Metadata Tracking Service (MTS)" / "metadata" framing.
- [ ] `hippo/README.md` — product description.
- [ ] `hippo/design/` — `INDEX.md`, `sec1_overview.md`, and any "metadata" framing in the spec.
- [ ] Keep the *accurate* parts ("tracks where data lives" is one *role*, not the essence).
- **Acceptance:** Hippo's docs describe it as the structured domain graph / LinkML runtime; "where
  data lives" framed as a role. Commit in hippo, push, bump pin in drylims.

### 2. Dangling `platform/design/sec6_security_model.md`  *(in-tree)*
Referenced as authoritative by `aperture/design/decisions/ADR-0008`, `ADR-0016`,
`aperture/design/architecture.md`, `aperture/design/INDEX.md`, and `proposals/aperture-split.md`,
but **the file does not exist.**
- [ ] **Decide:** write `sec6_security_model.md` (preferred — consolidate the security model:
  Bridge = sole PEP/PDP, Hippo auth-unaware, capability-scoped client, field-mask + predicate
  pushdown, and the hippo#54 / drylims#27 findings) **or** downgrade/redirect the references.
- **Acceptance:** every reference to `sec6_security_model.md` resolves (file exists) or is corrected.

### 3. Bridge role contradiction  *(in-tree)*
`platform/design/INDEX.md` calls Bridge a **"federation layer between BASS instances"**;
`bridge/design/sec1–sec6` + aperture ADR-0008/0016 + the auth issues call it the **auth gateway
(PEP/PDP)**. The auth-gateway framing is far more developed and appears canonical — **confirm, then
reconcile** (don't silently pick).
- [ ] Reconcile `platform/design/INDEX.md` Bridge entry with `bridge/design/*` and the aperture ADRs.
- **Acceptance:** one consistent Bridge role across platform INDEX, bridge specs, and aperture ADRs.

### 4. Aperture's own top-level framing  *(aperture submodule)*
- [ ] `aperture/design/INDEX.md` — title/header still "Config-Driven Data Portal".
- [ ] `aperture/README.md` — product description.
- [ ] `aperture/design/portal-vision-handoff.md` — historical; **annotate** as superseded by
  `vision.md` rather than rewriting (it's a captured artifact).
- **Acceptance:** Aperture's lead framing is "AI-native explorer; portal = substrate," consistent
  with `vision.md`. Commit in aperture, push, bump pin in drylims.

### 5. drylims root docs  *(in-tree)*
- [ ] Root `CLAUDE.md` — component descriptions (Hippo "metadata tracking"; Aperture "interface
  layer / portal").
- [ ] Root `README.md` — platform/component descriptions.
- **Acceptance:** root docs reflect the domain-graph model and Aperture's reframe.

## Definition of done
- A repo-wide grep (including submodules) for `metadata store`, `Metadata Tracking`, and
  `data portal` (used as the *product* framing) returns only intentional/historical mentions
  (e.g. annotated handoff docs).
- Every `sec6_security_model.md` reference resolves.
- Bridge's role is stated identically across platform, bridge, and aperture docs.
- All checklist boxes ticked; submodule pins bumped; everything pushed.

## Out of scope (tracked elsewhere — do NOT do here)
Build/probe work from the strategic review is **not** part of this doc pass: DS-2 (Hippo GraphQL
filter/aggregation capability check), the introspection→derived-binding spike, the capability-scoped
Worker sandbox, the ADR-0010 KM-curve probe, and the auth issues (hippo#54, drylims#27). Leave these
for their own sessions.
