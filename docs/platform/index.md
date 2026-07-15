# DataHelix Platform

Cross-cutting documentation for the DataHelix platform — architecture decisions, deployment patterns, and shared concepts that span all components.

DataHelix is a modular, open-source software ecosystem designed to streamline bioinformatics workflows. Each component can be used independently or as part of the complete system.

## Components

| Component | Role | Status |
|---|---|---|
| [Mosaic](../mosaic/index.md) | Structured domain graph (LinkML runtime) | Design complete, implementation ready |
| [Cappella](../cappella/index.md) | Integration & harmonization engine | Design complete |
| [Aperture](../aperture/index.md) | Interface layer (CLI, web, API clients) | Design complete (CLI v0.1) |
| [Bridge](../bridge/index.md) | Integration middleware (auth, routing) | Design complete |
| [Canon](../canon/index.md) | Semantic artifact resolver | Design complete |

## Platform Documentation

- [Overview](src/overview.md) — High-level platform introduction
- [Architecture](src/architecture.md) — System architecture and component interactions
- [Getting Started](src/getting-started.md) — First steps with DataHelix
- [Deployment](src/deployment.md) — Deployment guide
- [Glossary](src/glossary.md) — Key terms and definitions

## Platform Design Specification

- [Platform Overview](src/design/sec1_overview.md)
- [Component Architecture](src/design/sec2_components.md)
- [Integration Patterns](src/design/sec3_integration.md)
- [Unified Ingestion](src/design/sec4_unified_ingestion.md)
- [Integration Test Strategy](src/design/sec5_integration_test_strategy.md)
