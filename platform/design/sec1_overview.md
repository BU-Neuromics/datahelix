## 1. Platform Overview & Vision

**Document status:** Draft v0.1
**Last updated:** 2026-03-31
**Depends on:** Component sec1 docs (Hippo, Cappella, Canon, Aperture, Bridge)
**Feeds into:** sec2_components.md, sec3_integration.md, deployment docs, getting-started guide

---

### 1.1 What DataHelix Is

**DataHelix** is an open-source, modular platform for
managing and analyzing biological research data. It provides a unified foundation for:

- **Metadata management** — a single, queryable registry of entities (subjects, samples,
  datafiles, analysis outputs) with full provenance
- **Artifact resolution** — deterministic, reproducible resolution of where canonical output
  files live for any set of input entities
- **Data harmonization** — automated ingestion and consistency enforcement across external
  laboratory information systems (LIMS), clinical databases, and analysis pipelines
- **Access control** — optional authentication and authorization for shared deployments

DataHelix is designed for **research labs and institutions** working with high-dimensional
biological data: genomics, transcriptomics, spatial biology, clinical omics, and related
fields. It targets the gap between raw data files and downstream analyses — the metadata
and logistics layer that is often managed via spreadsheets, ad hoc scripts, and institutional
inertia.

---

### 1.2 Design Principles

#### 1.2.1 Modularity — Use What You Need

DataHelix components are independently installable and usable. A researcher who only needs the
structured domain graph (e.g. for metadata tracking) can install Hippo alone; a team that additionally needs file artifact
resolution adds Canon; a lab with external LIMS systems adds Cappella for integration; a
multi-user deployment adds Bridge for auth.

No component requires another as a runtime dependency. Integration is opt-in.

#### 1.2.2 SDK-First Architecture

All business logic lives in Python SDKs. REST APIs and GraphQL (future) are thin transport
wrappers over the same SDK logic. This means:

- Local use (laptop, notebook) is as capable as server-mode use
- The REST API does not expose capabilities that the SDK does not
- Components can be used programmatically without running a server

#### 1.2.3 Progressive Deployment

The same codebase runs from a single researcher's laptop to an institutional cloud:

| Scale | Components | Auth | Storage |
|---|---|---|---|
| Individual researcher | Hippo + Canon SDK only | None | SQLite |
| Small lab | Hippo + Cappella + Aperture CLI | None (or Bridge API keys) | SQLite |
| Multi-user team | All components + Bridge | Bridge API keys | SQLite or PostgreSQL |
| Institution | All components + Bridge | Bridge OIDC | PostgreSQL |

Scale is controlled entirely by configuration. No code changes required to move between
tiers.

#### 1.2.4 Provenance by Default

Every data mutation in Hippo records who changed what, when, and via which path. This is
not an add-on — it is fundamental to the data model. Provenance enables:

- Reproducibility: trace the origin of any entity back to its source
- Debugging: find when and how an incorrect value was introduced
- Auditing: demonstrate to collaborators or reviewers what changed in the dataset

#### 1.2.5 Config-Driven Domain Adaptation

DataHelix is domain-agnostic at the platform level. Entity types, fields, relationships, and
validation rules are defined by deployment-specific configuration files (`schema.yaml`,
`validators.yaml`). The same DataHelix codebase runs for a genomics lab, a cell therapy program,
a clinical biobank, or a plant biology consortium — with different configurations.

---

### 1.3 Platform Scope

#### In Scope

| Capability | Primary Component |
|---|---|
| Entity metadata storage and querying | Hippo |
| Data provenance and audit trail | Hippo |
| File artifact resolution | Canon |
| External system ingestion (LIMS, REDCap, CSV) | Cappella |
| Pipeline execution and output ingestion | Cappella |
| Command-line interface for researchers | Aperture |
| Multi-user authentication and access control | Bridge |
| Cross-component data consistency | Bridge |

#### Out of Scope (v1.0)

| Capability | Status | Notes |
|---|---|---|
| Bioinformatics analysis execution | Out of scope | DataHelix manages data about analyses, not analyses themselves (except file cache in Canon) |
| File storage and data transfer | Out of scope | DataHelix stores paths/URIs, not file contents |
| Web portal (beyond CLI) | Deferred to v1.1+ | Aperture web portal in design; CLI ships in v1.0 |
| GraphQL API | Deferred to v1.1 | REST first; GraphQL gateway via Bridge in v1.1 |
| Multi-institution federation | Deferred to v2.0 | Bridge as inter-DataHelix federation layer — needs design |
| Full RBAC and OAuth 2.0 | Deferred to v1.1 | v1.0 ships API key auth only |

---

### 1.4 Relationship to Existing LIMS Systems

DataHelix is **not a replacement for existing LIMS systems** (STARLIMS, REDCap, LabKey, etc.).
It is a **metadata intelligence layer that aggregates and harmonizes data from those systems**.

Existing LIMS systems continue to be the system of record for wet-lab operations (sample
tracking, accessioning, clinical data entry). Cappella pulls from those systems and
harmonizes the results into Hippo's canonical schema. Researchers query Hippo for analysis
rather than querying multiple upstream systems directly.

```
STARLIMS   REDCap   Clinical DB   Sequencing Core
    │          │          │              │
    └──────────┴──────────┴──────────────┘
                          │
                     Cappella
                    (harmonize)
                          │
                        Hippo
                    (canonical store)
                          │
                Canon + Aperture
                  (query + resolve)
```

---

### 1.5 v1.0 Scope and Release Criteria

Platform v1.0 is the first production-ready release of the full component stack.

**v1.0 components:**
- Hippo v0.4+ (stable structured domain graph / LinkML runtime, REST API, provenance, schema migrations)
- Canon v0.3+ (artifact resolution, CWL execution integration, storage adapters)
- Cappella v0.2+ (trigger engine, external adapters, reconciliation)
- Aperture v0.1 (CLI: entity CRUD, schema inspection, provenance, auth commands)
- Bridge v0.1 (API key auth, request routing, cross-component sync)

**v1.0 exit criteria:**
- A new user can install, configure, and complete the getting-started walkthrough
  using only the documentation
- Full integration test suite (round-trip: external source → Cappella → Hippo → Canon)
  passes in CI
- Docker Compose single-node deployment works from a clean machine
- All components have tagged releases and documented changelogs

---

### 1.6 Open Questions

| Question | Priority | Status |
|---|---|---|
| Platform name | Low | Settled as **DataHelix**. |
| Multi-institution federation model | Medium | Candidate: Bridge as federation gateway; needs design for v2.0 |
| GraphQL gateway scope for v1.1 | Low | Open |
