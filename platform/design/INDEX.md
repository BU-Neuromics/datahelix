# BASS Platform — Architecture Design Index

**Status:** Living document  
**Last updated:** 2026-03-13  

This document records cross-cutting architectural decisions that apply to the BASS platform as a whole. Decisions that affect only a single component are recorded in that component's `design/INDEX.md`. This document takes precedence where conflicts exist.

---

## Document Map

| File | Topic | Status |
|---|---|---|
| `INDEX.md` (this file) | Platform-level decisions log and open questions | 🔄 Active |
| *(future)* `sec1_overview.md` | Platform vision, scope, and component relationships | ⬜ Not started |
| *(future)* `sec2_components.md` | Component responsibilities and boundaries | ⬜ Not started |
| *(future)* `sec3_integration.md` | Inter-component interfaces and contracts | ⬜ Not started |

---

## Key Decisions Log

### Component Responsibilities

| Decision | Choice | Rationale |
|---|---|---|
| Cappella's primary role | Integration and harmonization engine — the "conductor" that coordinates all data sources | Cappella ingests from external systems (HALO, STARLIMS, REDCap, partner omics, internal workflows), harmonizes data, and writes into Hippo. Not primarily a workflow executor (though workflow output ingestion is in scope). |
| Cappella's storage backend | Hippo exclusively — Cappella is stateless | Cappella does not own any data. All persistent state lives in Hippo. |
| Workflow execution scope | In scope for Cappella — pipeline runs are treated as a data source like any other | A workflow run takes Hippo entities as inputs, produces outputs (datafiles, QC metrics, derived entities), and Cappella captures inputs/outputs/provenance back into Hippo. The executor and the integration engine are unified. |
| Bridge scope | Deferred — not yet defined | Candidate role: federation layer between BASS instances (inter-institutional data sharing). Not a required component for single-institution deployments. |

### Adapter Boundaries (Hippo vs. Cappella)

| Decision | Choice | Rationale |
|---|---|---|
| External system adapter implementations | Live in Cappella | STARLIMS, HALO, REDCap, partner system connectors belong to the integration layer, not the storage layer. |
| `ExternalSourceAdapter` ABC | Stays in Hippo | Hippo defines the interface contract. Cappella (and third parties) provide implementations. Consistent with the `EntityStore` adapter pattern. |
| Field mapping and transformation config | Lives in Cappella adapter config | Hippo schema defines the *target* (canonical entity types and fields). Cappella adapter config defines the *mapping* from source system fields to Hippo fields. These are separate concerns in separate files. |
| Data cleaning and vocabulary normalization | Cappella adapter responsibility | Controlled vocabulary normalization (e.g., mapping variant spellings of anatomy labels to canonical FMA terms) is deployment-specific logic and belongs in the Cappella adapter layer, not Hippo. |
| Hippo external adapter stubs (STARLIMS, HALO, Donor DB) | To be removed from Hippo in a future spec update | Currently stubbed in `hippo/adapters/external/`. These implementations should migrate to Cappella. The `ExternalSourceAdapter` ABC remains in Hippo. |

### Reference Data and Canonical Identifiers

| Decision | Choice | Rationale |
|---|---|---|
| Reference ontology data (FMA, Ensembl, etc.) | Stored in Hippo as regular entities | `AnatomyTerm`, `Gene`, and similar reference types are defined in the schema config like any other entity type and loaded via batch ingestion at deployment time. |
| Canonical anatomy identifier | Foundational Model of Anatomy (FMA) | FMA is the authoritative reference for anatomy labels across the platform. |
| Canonical gene identifier | Ensembl gene ID | All gene references resolve to Ensembl IDs. Other identifiers (Entrez ID, gene symbol, RefSeq) are stored as ExternalIDs against the canonical `Gene` entity. |
| Gene identifier cross-referencing | Hippo `ExternalID` system (§3.4) | Entrez IDs, gene symbols, and other identifier systems map to a single canonical `Gene` entity UUID via Hippo's existing external ID machinery. No new mechanism required. |
| Reference data loading | Cappella responsibility via a dedicated "reference data" adapter | A special Cappella adapter loads FMA OWL, Ensembl GTF, etc. at deployment time. Hippo deployment docs must call this out as a prerequisite step. |

### Search and Fuzzy Lookup

| Decision | Choice | Rationale |
|---|---|---|
| Fuzzy search abstraction | Implemented at the storage adapter level | The `EntityStore` ABC gains a `search` method. Each adapter implements fuzzy lookup using backend-appropriate mechanisms (SQLite FTS5, PostgreSQL pg_trgm, vector similarity, etc.). Cappella sees a uniform API regardless of backend. |
| Per-field search mode declaration | Declared in schema config per field (`search: fts \| embedding \| synonym`) | Intent is declared in the schema; implementation is the adapter's concern. Supports different strategies for different field types. |
| `ScoredMatch` response type | Core SDK type (adapter-agnostic) | Fields: `entity_id`, `entity_type`, `field`, `value`, `score` (0.0–1.0), `match_mode`. Cappella configures confidence thresholds per match mode in its adapter config. |
| Adapter capability declaration | Each adapter publishes supported search modes | Hippo validates at startup that schema-declared search modes are supported by the active adapter. Fails fast with a clear error on mismatch. Prevents silent degradation. |
| Resolution logic and confidence thresholds | Cappella adapter config | Hippo returns ranked candidates with scores. Cappella decides what to do with them (accept, flag for review, reject) based on deployment-specific thresholds. |

---

## Open Questions

| Question | Priority | Notes |
|---|---|---|
| Bridge: federation layer vs. other role? | Medium | Candidate: inter-BASS-instance data sharing for multi-institution deployments. Needs more design before a component spec can be started. |
| Platform name | Low | BASS is unsatisfactory. drylims is acceptable but not ideal. Revisit when higher-priority design work is complete. |
| Cappella config format | High | Adapter configs need to express more than field-to-field mappings — transformation pipelines with rules, vocabulary normalization, confidence thresholds. Format TBD. |
| Reference data versioning | Medium | FMA and Ensembl release versions change. How does Hippo track which version of a reference ontology is loaded? Does updating a reference ontology trigger entity migrations? |
| Cappella trigger model | High | What initiates a Cappella sync? Options: event-driven (webhooks from source systems), scheduled (cron), manual, or pipeline-triggered. Likely all of the above — needs a unified model. |
| Multi-institution deployment model | Medium | If Bridge is a federation layer, what does a federated query look like? Does each institution run a full BASS stack? What data leaves the institution boundary? |
| Workflow executor integration | Medium | Does Cappella wrap an existing executor (Nextflow, Snakemake) or define its own? How are workflow definitions versioned and stored? |

---

## Component Responsibility Summary

| Component | Owns | Does not own |
|---|---|---|
| **Hippo** | Canonical entity schema, storage backends, `ExternalSourceAdapter` ABC, `EntityStore` ABC, provenance log, fuzzy search interface (SDK), `ScoredMatch` type | External system connector implementations, field mapping config, harmonization logic, workflow execution |
| **Cappella** | External system adapter implementations, field mapping and transformation config, harmonization logic, vocabulary normalization, workflow orchestration and output ingestion, reference data loading | Storage, canonical schema definition, provenance |
| **Aperture** | User-facing query interface (CLI, web, API clients) | Business logic, storage, integration |
| **Bridge** | TBD — candidate: inter-BASS-instance federation | TBD |

---

## Design Session Notes

**2026-03-13** — Initial platform architecture session (Adam + Stanley).  
Topics covered: Cappella scope and conductor metaphor, adapter boundary between Hippo and Cappella, field mapping ownership, reference data model, fuzzy search abstraction, gene/anatomy canonical identifiers. All decisions above recorded from this session.
