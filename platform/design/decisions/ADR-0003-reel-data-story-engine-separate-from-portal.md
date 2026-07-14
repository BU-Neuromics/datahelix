# ADR-0003: Separate the data-story engine (Reel) from the rendering portal (Aperture)

- **Status:** Accepted
- **Date:** 2026-06-22 (decided); executed 2026-06 — see **Outcome**
- **Deciders:** labadorf, design session
- **Related:** `platform/design/view-contract.md` (the joining interface); Aperture `design/vision.md` (the 2026-06-17 reframe); Aperture ADR-0022–0025 (instruction-path / data-story model) and ADR-0026 (headless core + thin shell), both **migrated to Reel** on the split; the [`BU-Neuromics/reel`](https://github.com/BU-Neuromics/reel) repository (the extracted component); `proposals/hippo-split.md` / `proposals/aperture-split.md` (the split pattern this followed)

> **Name.** The extracted engine is **Reel** (a reel of frames ≈ a sequence of data-story
> states; stays in Aperture's optical family). It was a working codename at decision time
> (candidates: Strand, Loom, Lumen, Cadence); it was ratified and is now the component's real
> name — see the [`reel`](https://github.com/BU-Neuromics/reel) repo.

## Outcome (recorded 2026-07-14)

This decision was executed. **Reel now lives in its own repository,
[`BU-Neuromics/reel`](https://github.com/BU-Neuromics/reel)**, with its own design set (vision,
instruction-path model, and ADRs). The Aperture headless-core ADR-0026 cited below migrated to
**Reel ADR-0005** ("Reel is a headless interaction core + a thin, replaceable shell"), which
carries a forward pointer back to it. The **View Contract** stub referenced throughout is landed
alongside this ADR at [`platform/design/view-contract.md`](../view-contract.md); Reel's ADRs
reference it as the platform-level producer/consumer seam.

This ADR is preserved as the record of the *component-boundary decision* itself; the detail of
Reel's internal design is owned by the Reel repo and has evolved past what is sketched here.

## Context

The 2026-06-17 reframe (Aperture `design/vision.md`) recast Aperture from a config-driven data
portal into an **AI-native data & workflow explorer**, with the portal as its *substrate*, not
the product. That reframe is **decided — not relitigated here**.

In the design sessions since, the AI-native core — the **data-story / instruction-path model**
(Aperture ADR-0022–0025: source-tagged typed instructions reducing to subgraph states +
artifacts, as-of reproducibility, topology, mid-path recompute) and the **headless core**
boundary (Aperture ADR-0026) — has grown into the most ambitious and least-proven part of the
whole platform. It is also gated on an unrun keystone probe. Meanwhile the thing that can be
**deployed to real users now** is the comparatively boring, well-understood **config-driven
portal** (the substrate). The ambitious core is **blocking a shippable MVP**.

A design insight resolves the tension: the data-story core does not need to render anything. It
can **produce data according to a self-describing contract** that is sufficient for *any*
consumer to visualize by its own mechanisms — the **Vega-Lite pattern** (a declarative grammar +
bound data realized by a renderer that the producer knows nothing about; already cited in
Aperture's `design/prior-art.md`). "An OpenAI-model-spec-style declarative spec, but with the
data attached." Once the core emits a contract rather than pixels, **the renderer and the engine
are no longer one thing** — and the portal can ship against the contract without waiting on the
engine.

This ADR is therefore a **component-boundary decision** (hence platform-level, not
Aperture-internal): does the data-story engine belong *inside* Aperture, or is it its own
component joined to Aperture by a contract?

## Decision

**Split the data-story engine into its own component, joined to the portal by a
renderer-agnostic view contract.** Three pieces, currently conflated inside "Aperture":

1. **Aperture — the portal (renders; the deployable MVP).** A config-driven data portal over
   Mosaic's GraphQL, which *renders* view contracts into a usable UI for end users. This is what
   Aperture ADR-0002–0017 actually specced; it ships now. Aperture is **re-scoped to the
   portal**.
2. **Reel — the data-story engine (headless; produces contract instances).** The instruction-path
   model (ADR-0022–0025) and headless-core boundary (ADR-0026), extracted into its own component.
   Reel is **headless**: it produces **view-contract instances** (data + declarative spec) and
   does **no rendering**. It is the AI-native bet, now on its own timeline.
3. **The View Contract — the renderer-agnostic interface that joins them.** A declarative
   "spec-with-data-attached" standard (`platform/design/view-contract.md`): self-describing, so
   any consumer can render it without knowing its producer. Both Reel **and** the Aperture portal
   *emit* contract instances; any renderer (the portal, a notebook, a third-party tool) *consumes*
   them. **Basic portal views are emitted directly from config and need no Reel at all.**

**Mechanics.** Reel is extracted to its own repository and re-attached to the DataHelix platform
repo as a submodule, following the established `proposals/hippo-split.md` /
`proposals/aperture-split.md` pattern. The data-story ADRs (Aperture ADR-0022–0025) and the
headless-core ADR (ADR-0026) **migrate to Reel** (superseded in Aperture with a forward pointer);
the View Contract becomes a platform-level interface spec referenced by both.

**This is not a reversal of the reframe.** It *honors* the reframe's own "portal = substrate"
framing by (a) letting the substrate ship independently as a product now, and (b) giving the
AI-native explorer its own component so it can mature without holding the portal hostage. The
north star (an AI-native explorer over the domain graph) is unchanged; only the component
boundary is drawn.

## Consequences

- **The portal MVP is unblocked.** Aperture ships against the View Contract using
  config-emitted views; it does not wait on Reel or the keystone probe.
- **The AI-native vision is preserved, decoupled.** Reel carries the ambitious, less-proven work
  (and the reframed keystone probe — *"can an LLM drive a typed declarative artifact through a
  validator to a correct change?"*) on its own release cadence. If Reel slips, the portal still
  ships; if Reel succeeds, the portal renders its contract instances unchanged.
- **The View Contract becomes a first-class platform interface**, with more than one producer
  (Reel, the portal) and many possible consumers — exactly the kind of cross-component contract
  `platform/design/` exists to own.
- **Cross-component dependencies link both ways:** Reel ADRs cite the View Contract; the portal
  cites it; the contract spec lists its producers/consumers.
- **Aperture's own ADRs are re-scoped** (submodule): ADR-0022–0025 + ADR-0026 superseded with
  forward pointers to Reel; ADR-0002–0021 remain the portal's decisions.

## Alternatives considered

- **Keep everything in one Aperture component (status quo).** The ambitious data-story engine
  keeps blocking the deployable portal, and the renderer stays welded to the engine. Rejected —
  it is the exact problem this ADR exists to remove.
- **Keep the engine inside Aperture as an internal module (not a separate component).** Lighter
  process, but it couples release cadence and ownership: the portal can't ship a stable version
  while the engine churns, and "headless core" stays a boundary inside one repo rather than a
  contract between two. Rejected — a contract between components is the cleaner seam and matches
  how Mosaic/Cappella/Canon are factored.
- **Fold the contract into Aperture only (portal-private view format).** Loses the entire point:
  the contract's value is that *any* consumer (notebooks, third-party tools, future DataHelix
  UIs) can render Reel's output. A portal-private format re-welds producer to renderer. Rejected.
- **Don't extract; just defer the data-story work.** Preserves one component but loses the
  decoupling — the work would still live in Aperture's design and re-entangle. Rejected: the
  split *is* the deferral mechanism, done cleanly.

## Notes / open sub-questions

- **View Contract shape.** Stubbed in `platform/design/view-contract.md`; the detailed grammar
  (primitive catalog, data-binding, how much of Aperture ADR-0010's vocabulary it absorbs) is its
  own design pass. The contract is what Aperture ADR-0009/0010 were circling; this elevates it to
  a platform standard.
- **Submodule mount.** The DataHelix repo does not yet mount `reel` as a submodule (the design
  lives in `BU-Neuromics/reel` and is consumed there); wiring it into the unified docs/site is
  follow-on integration work, not part of this boundary decision.
