# Cappella — Integration & Harmonization Engine

!!! success "v0.1 Implemented"
    Cappella v0.1 is fully implemented with all 27 features passing across 8 epics, including the adapter system, collection resolver, trigger engine, reconciliation, REST API, and CLI.

Cappella is the **harmonization engine** of the BASS platform. Like voices singing *a cappella* — in harmony, without instrumentation — Cappella takes data arriving from many different sources and makes them sing together in a single, consistent, provenance-rich picture stored in Hippo.

Cappella answers the question: **"Is everything we know about this subject consistent, present, and correct?"**

## Who Is Cappella For?

- **Data managers** who receive metadata from multiple systems (LIMS, clinical databases, sequencing cores) and need it unified in one place
- **Researchers** who need a resolved collection of files and metadata for a specific research question — without tracking down files manually
- **Platform operators** who need automated, auditable data ingestion pipelines with reconciliation and conflict detection

## When to Use Cappella

Use Cappella when you need to:

- **Ingest from multiple sources** — Pull records from STARLIMS, HALO, REDCap, CSV files, SQL databases, or custom adapters and normalize them into Hippo's schema
- **Resolve collections** — Ask "give me all aligned reads for CTE DLPFC samples" and get back a fully resolved, provenance-tracked JSON with file URIs
- **Detect inconsistencies** — Find donors that exist in one source but not another, or field values that differ between systems
- **Automate syncs** — Run ingestion on a schedule, on-demand, or in response to events

Cappella is **stateless** — all persistent data lives in Hippo. Cappella can be restarted at any time without data loss.

## Key Features

- **Multi-source ingestion** — Pull structured data from external sources (STARLIMS, HALO, REDCap, sequencing cores) via adapter plugins
- **Harmonization** — Transform fields to the canonical Hippo schema, validate consistency, upsert via ExternalID
- **Collection resolution** — Query Hippo to find matching entities and resolve file URIs via Canon
- **Reconciliation** — Monitor for inconsistencies across sources and surface structured audit events
- **Trigger engine** — Execute ingest and resolution operations on schedule, webhook, poll, or manual triggers

## Key Concepts

| Concept | Description |
|---|---|
| **Adapter** | A plugin that connects to an external data source (CSV, JSON, SQL, or custom). Each adapter knows how to pull records and map fields to Hippo schema. |
| **HarmonizedCollection** | The output of collection resolution — a structured JSON containing matched entities, resolved file URIs, and full provenance. |
| **Selection strategy** | Logic for choosing between alternatives when multiple datasets exist for a sample (e.g., prefer most recent, highest QC score). |
| **Trigger** | An automation rule that executes ingest or resolution operations. Types: `schedule`, `manual`, `internal_event`. |
| **Reconciliation** | Active detection of inconsistencies between sources or between external systems and Hippo. |
| **ExternalID** | The key used to match external records to Hippo entities — create if absent, update if changed. |

## Architecture Overview

Cappella sits between external data sources and Hippo, with Canon providing file resolution:

```
Aperture / Composer  ← user interface, aggregate analysis
       │
    Cappella          ← harmonize sources, resolve collections
     │    │
   Canon  Adapters   ← file resolution | STARLIMS, HALO, REDCap, CSV, SQL
       │
    Hippo             ← entity store (sole persistent state)
```

Cappella does not own data, run analyses, or manage files. It coordinates data flow into Hippo and assembles resolved collections for downstream consumers.

## Getting Started

```bash
pip install cappella
cappella serve
```

See the **[Quick Start guide](docs/quickstart.md)** for a complete walkthrough — from configuration through your first ingestion and collection resolution.

## Related Components

- [Hippo](../hippo/index.md) — Cappella's sole persistent store; all harmonized data is written to Hippo
- [Canon](../canon/index.md) — Cappella calls `canon.resolve()` for artifact resolution during collection assembly
- [Aperture](../aperture/index.md) — Users request collections and trigger ingestion via Aperture
- [Bridge](../bridge/index.md) — Provides authentication for multi-user Cappella deployments

## User Documentation

- [Introduction](docs/introduction.md) — Detailed overview
- [Installation](docs/installation.md) — Setup instructions
- [Overview](docs/overview.md) — Architecture overview
- [Quick Start](docs/quickstart.md) — Get running quickly
- [User Guide](docs/user_guide.md) — Complete usage guide
- [Workflows](docs/workflows.md) — Workflow definitions and patterns

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [Adapter System](design/sec3_adapters.md)
- [Audit & Observability](design/sec4_audit.md)
- [Collection Resolution Workflow](design/sec5_workflows.md)
- [Non-Functional Requirements](design/sec6_nfr.md)
- [Trigger Engine Test Strategy](design/sec7_testing.md)
