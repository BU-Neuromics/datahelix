# The View Contract — a renderer-agnostic data + declarative-spec interface

**Status:** 🟠 Stub / working design (2026-06-22). Created by
[`decisions/ADR-0003`](./decisions/ADR-0003-reel-data-story-engine-separate-from-portal.md) as
the interface that joins the **Reel** data-story engine
([`BU-Neuromics/reel`](https://github.com/BU-Neuromics/reel)) to the **Aperture** portal. The
grammar below is a skeleton to be fleshed out in its own design pass; it is **not** yet binding.

> **Naming.** "View Contract" is descriptive; it may earn a codename later (candidates: *Frame*,
> *Plate* — photographic, matching Aperture/Reel). Reel's own ADRs reference this file as the
> platform-level producer/consumer seam.

## What it is

A **View Contract instance** is a single, self-describing, serializable artifact that carries
**both** a declarative description of *what to show* **and** the **data to show**, such that any
conforming consumer can render it **without knowing how it was produced**. It is the platform's
answer to "the engine produces data according to a contract that is enough for consumers to
visualize by their own mechanisms" (ADR-0003).

The reference pattern is **Vega-Lite** (cited in Aperture's `design/prior-art.md`): a declarative
grammar + bound data that a renderer realizes, with the producer knowing nothing about the
renderer. Framed another way: *an OpenAI-model-spec-style declarative spec, but with the data
attached.*

It is **not** DOM, HTML, JSX, or a component tree (consistent with Aperture ADR-0009:
view-descriptions, never direct rendering). It is **not** a transform/expression language
(consistent with Aperture ADR-0004: nouns, not verbs — no middle scripting layer).

## Why it is a platform-level interface

The contract has **more than one producer and many consumers**, so it cannot live inside any one
component (ADR-0003):

```
   PRODUCERS                      CONTRACT                 CONSUMERS (renderers)
 ┌───────────────┐                                       ┌────────────────────┐
 │ Reel          │  emits ─┐                      ┌─────►│ Aperture portal     │
 │ (data-story   │         │   ┌───────────────┐  │      ├────────────────────┤
 │  engine)      │         ├──►│ View Contract │──┼─────►│ Notebook / widget   │
 ├───────────────┤         │   │  spec + data  │  │      ├────────────────────┤
 │ Aperture      │  emits ─┘   └───────────────┘  └─────►│ Third-party tool    │
 │ portal config │                                       └────────────────────┘
 └───────────────┘
```

Basic portal views are emitted **directly from config** (no Reel); rich data stories are emitted
by **Reel**. Both speak the same contract, so any renderer handles both.

## Design skeleton (to be fleshed out)

A contract instance is roughly:

```
ViewContract:
  spec:                      # declarative "what to show" — the noun-catalog (no verbs)
    primitive: <type>        #   e.g. table | faceted-list | key-value | line | bar |
                             #   scatter | km-curve | heatmap | layout-container | ...
    params: { ... }          #   typed parameters for the primitive
    encoding: { ... }        #   how data fields map onto the primitive's channels
    children: [ ViewContract ]   # composition: declarative nesting (Aperture ADR-0015)
    links: [ <typed link> ]  # cross-links as typed nouns → logical targets (ADR-0015)
  data:                      # the data to show — attached, self-contained
    rows / records / series  #   evaluated from the producer's query
    schema_ref: <type info>  #   enough type info for the renderer to interpret fields
  provenance: { ... }        # optional: as-of watermark, producing instruction (Reel)
```

The primitive catalog and binding rules are inherited from where Aperture ADR-0009/0010 were
heading (the **typed noun-catalog vocabulary**); this spec is where that vocabulary becomes a
**shared standard** rather than an Aperture-internal type.

## Invariants (carried from the Aperture ADRs the contract absorbs)

- **Self-contained.** A renderer needs *only* the instance — no callback to the producer to
  paint it. (Interactivity that needs new data is a *new* contract instance, produced by the
  engine, not a renderer escape hatch.)
- **Nouns, not verbs.** The spec selects from a closed, typed primitive catalog; it carries no
  transforms/expressions (Aperture ADR-0004). Heavy computation happened upstream (query /
  Reel op), not in the contract.
- **Headlessly validatable.** A contract instance can be validated with no browser (Aperture
  ADR-0009) — the producer's dry-run gate and the consumer's "can I render this?" check use the
  same schema.
- **Degrades gracefully.** Absent/masked fields (Bridge field masks; unpersisted multivalued
  slots) render as "not available," never errors (Aperture ADR-0016).
- **Architecture-neutral links.** A cross-link names a *logical* target (entity type + id, or
  named view + params), not an href — the renderer realizes routing (Aperture ADR-0015).

## Open questions

- **How much of Aperture ADR-0010's vocabulary moves here** vs. stays renderer-side? (Lean: the
  *catalog of primitives + encodings* is the contract; pixel realization is the renderer's.)
- **Versioning.** The contract is a wire format between independently-released components — it
  needs additive-compatibility rules (cf. Mosaic's additive-only GraphQL tolerance).
- **Data shape.** Inline rows vs. a reference the renderer fetches (for large results) — and how
  that interacts with the as-of watermark for reproducibility (Reel's reproducibility ADR).
- **Conformance.** What is the minimum a renderer must support to claim "renders the View
  Contract"? (A capability-declaration pattern, like Aperture's layer-D source adapter.)
- **Relationship to Mosaic's GraphQL types.** The `schema_ref` likely derives from Mosaic's
  `schema_typing` so a renderer can interpret fields without a second type system.
