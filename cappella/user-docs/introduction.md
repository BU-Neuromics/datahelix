# Introduction to Cappella

Cappella is the **harmonization engine** of the BASS (Bioinformatics Analysis Support System) platform. Its name reflects its role: like voices singing *a cappella* — in harmony, without instrumentation — Cappella takes data arriving from many different sources and makes them consistent in a single, provenance-rich picture.

## The Core Idea

Research data lives in many places. Donors are tracked in a LIMS. Clinical assessments come from REDCap. Histopathology scores come from HALO. Sequencing manifests come from the sequencing core. Computed analysis files come from Canon. Each source has its own schema, identifiers, and update cadence.

Cappella's job is to pull all of this together into **Hippo** — the platform's entity store — and ensure everything is internally consistent: field names normalized, vocabulary standardized, references correctly linked, and every change provenance-tracked.

## What Cappella Does

**Ingest & harmonize** — Pull records from external sources via configurable adapters (CSV, JSON, SQL, custom), transform field names and vocabulary, detect conflicts between sources, and upsert into Hippo.

**Resolve collections** — Given a research question like "give me all gene counts for CTE DLPFC donors," Cappella queries Hippo to find matching entities, selects the right dataset per sample, and calls Canon to ensure required files are materialized. Returns a structured `HarmonizedCollection` JSON with resolved URIs and provenance.

**Reconcile** — Actively detect inconsistencies: a donor present in an external system but missing from Hippo, a field value that differs between two trusted sources, a sample with no associated sequencing data.

**Trigger** — Automate ingest and resolution on a schedule, on-demand via the CLI or API, or in response to internal events.

## What Cappella Is Not

**Cappella does not run analyses.** DESeq2, clustering, QC pipelines — these are downstream concerns for Composer or custom scripts. Cappella delivers resolved file URIs; consumers decide what to do with them.

**Cappella does not manage files.** File storage, caching, and computation are Canon's domain. Cappella calls Canon and receives back URIs.

**Cappella does not own data.** All persistent state lives in Hippo. Cappella is entirely stateless — it can be restarted without data loss.

## Platform Architecture

```
Aperture / Composer  ← user interface, aggregate analysis
       │
    Cappella          ← harmonize sources, resolve collections
     │    │
   Canon  Adapters   ← file computation | STARLIMS, HALO, REDCap, CSV, SQL
       │
    Hippo             ← entity store (all metadata + file URI pointers)
```

## Getting Started

→ [Quick Start](quickstart.md) — install, configure, and run your first ingest
→ [User Guide](user_guide.md) — adapters, triggers, resolution, reconciliation
→ [Design Specification](../design/INDEX.md) — architecture decisions and component boundaries
