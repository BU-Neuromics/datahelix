# DataHelix Platform — The Domain Graph (foundational data model)

**Status:** 🟢 Foundational concept (2026-06-17). Cross-cutting; takes precedence over
component-local framings where they conflict. Supersedes the "metadata store" framing of Hippo.
Origin: Aperture design session (see `aperture/design/vision.md`, `.../prefab/data-stories.md`).

## The reframe: one typed domain graph, not a "metadata store"

A DataHelix deployment is, conceptually, **one typed knowledge graph** — the *domain graph* — whose
type system is the deployment's **LinkML schema** and whose contents are everything the lab knows
about its biology and its data. "Metadata vs. data" is **not** a property of stored things; it is
a **role a node plays relative to a query**, assigned at query time. (A toxicology report is the
*subject* of one query and a *descriptor* in another; a graph has no privileged "fact table.")
We therefore stop calling Hippo a "metadata store." It is **the structured domain graph**.

The intrinsic boundary that *is* real is not data/metadata but:

> **structured relational records** (schema-conformant entities + attributes + relationships;
> low-to-moderate cardinality; queryable as a graph) — served by **Hippo**
> vs.
> **bulk opaque payloads** (sequence reads, expression matrices, images; high cardinality;
> array/columnar) — held as files, mediated by **Canon/Cappella**.

Both are subgraphs of the *same* domain graph; only the physical substrate and the
slice-extraction mechanics differ — and those are hidden from the user.

## "LinkML runtime" and "domain graph" are the same claim from two sides

- The **LinkML schema is the graph's type system**: classes = node types, relationship slots =
  edge types, scalar slots = node attributes, ranges/enums/constraints = semantic rules. LinkML
  is graph-native (it compiles to RDF/OWL/SHACL; `class_uri`/`slot_uri` are first-class). A LinkML
  schema *is* a typed property-graph definition.
- **Hippo is the runtime that reads that schema and *becomes* the graph it describes** —
  instantiating storage, validation, API, and query semantics from the schema at startup.
- Therefore "LinkML runtime" names the *mechanism* and "domain graph" names the *artifact*. They
  are one thing. **Every Hippo query returns a knowledge subgraph whose semantics are exactly the
  schema's.** Per-deployment schema ⇒ per-deployment graph semantics. The config-driven
  *relational* storage is an implementation detail of the graph — no more essential than files
  being the substrate for bulk data.

## Bulk data as induced subgraphs (the union model)

A rectangular/cube dataset is **isomorphic to a typed labeled subgraph**: a `samples × genes →
value` cube is a bundle of typed edges (`Sample —expression{value}→ Gene`); selecting a *slice* =
selecting a sub-bundle of edges = **inducing a subgraph**. So:

> A **data-slice request** against bulk storage **induces a subgraph** that **unions** with the
> records-subgraph Hippo returns, forming one query-result graph. Different physical substrate
> (relational rows / columnar arrays / HDF5 / zarr / files), **uniform graph semantics at the
> query surface.**

This is **Ontology-Based Data Access / Virtual Knowledge Graphs (OBDA/VKG)**: one conceptual
graph (the LinkML ontology) over heterogeneous sources; queries rewritten to source-native
operations; results lifted back into the graph. In DataHelix terms:

| Layer | OBDA role |
|---|---|
| **Hippo relational engine** | mapping for the *structured* substrate (records → subgraph) |
| **Canon / Cappella** | mappings for the *bulk* substrate (slice request → induced subgraph) |
| **Aperture capability-negotiated adapter** | client-side reflection: gates which graph operations a substrate can serve |

**Abstraction boundary (the design contract):** users and LLM agents operate on **uniform graph
semantics**; **expert developers implement the substrate→subgraph mappings (slicers) as typed,
validated components** — the "no middle scripting layer" discipline applied to data access. Done
right, queries and data "behave as we expect" regardless of where bits physically live. This is
the same place the structured/bulk boundary is crossed *deliberately*: a derived, structured
*view* of bulk data (a summary, an aggregation tier) is a subgraph promoted into the queryable
graph when a query earns it — not Hippo becoming a data warehouse.

## Honest flag: this layer is the platform's deep end

The model is sound and is the right north star. But **OBDA/VKG query rewriting and efficient
federated slice extraction is the single hardest thing in the platform** — query planning across
substrates, mapping maintenance, making the union performant. It is well-studied precisely because
it is hard. It is correctly **deferred** (Canon/Cappella, post-MVP). Nothing here should be read
as implying the federated graph is a cheap or free abstraction.

## Consequences

- **Retire "metadata store" for Hippo**; use "structured domain graph" (catalog / knowledge
  layer). "Tracks where data lives" is *one role* (file cataloging), not Hippo's essence. *(Done
  2026-06-17: Hippo's self-description (`hippo/CLAUDE.md`, `hippo/design/INDEX.md`, sec1) and the
  rest of the platform docs were brought into line by the reframe consistency pass —
  `proposals/reframe-consistency-pass.md`.)*
- **Query results are knowledge subgraphs.** Downstream surfaces (Aperture views, data stories)
  consume subgraphs; the cohort/selection object should be **grain-agnostic and re-rootable** (a
  position in the graph + predicates), since re-rooting the focal entity is exactly the
  metadata↔data role-swap made operational.
- **The structured/bulk boundary, not data/metadata, is the architectural line** between Hippo and
  Canon/Cappella — and it is crossed only by promoting derived structured views into the graph.
