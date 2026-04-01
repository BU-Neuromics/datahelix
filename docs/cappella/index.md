# Cappella — Integration & Harmonization Engine

!!! warning "Not Yet Implemented"
    Cappella is currently in the design specification phase. The architecture and adapter system are fully specified but no implementation is available yet.

Cappella is the **harmonization engine** of the BASS platform. Like voices singing *a cappella* — in harmony, without instrumentation — Cappella takes data arriving from many different sources and makes them sing together in a single, consistent, provenance-rich picture stored in Hippo.

Cappella answers the question: **"Is everything we know about this subject consistent, present, and correct?"**

## Key Features

- **Multi-source ingestion** — Pull structured data from external sources (STARLIMS, HALO, REDCap, sequencing cores) via adapter plugins
- **Harmonization** — Transform fields to the canonical Hippo schema, validate consistency, upsert via ExternalID
- **Collection resolution** — Query Hippo to find matching entities and resolve file URIs via Canon
- **Reconciliation** — Monitor for inconsistencies across sources and surface structured audit events
- **Trigger engine** — Execute ingest and resolution operations on schedule, webhook, poll, or manual triggers

## Related Components

- [Hippo](../hippo/index.md) — Cappella's sole persistent store; all harmonized data is written to Hippo
- [Canon](../canon/index.md) — Cappella calls `canon.resolve()` for artifact resolution during collection assembly
- [Aperture](../aperture/index.md) — Users request collections and trigger ingestion via Aperture
- [Bridge](../bridge/index.md) — Provides authentication for multi-user Cappella deployments

## User Documentation

- [Introduction](user-docs/introduction.md) — Detailed overview
- [Installation](user-docs/installation.md) — Setup instructions
- [Overview](user-docs/overview.md) — Architecture overview
- [Quick Start](user-docs/quickstart.md) — Get running quickly
- [User Guide](user-docs/user_guide.md) — Complete usage guide
- [Workflows](user-docs/workflows.md) — Workflow definitions and patterns

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [Adapter System](design/sec3_adapters.md)
- [Audit & Observability](design/sec4_audit.md)
- [Collection Resolution Workflow](design/sec5_workflows.md)
- [Non-Functional Requirements](design/sec6_nfr.md)
- [Trigger Engine Test Strategy](design/sec7_testing.md)
