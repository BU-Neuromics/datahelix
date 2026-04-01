# Hippo — Metadata Tracking Service

Hippo is an open-source, configurable metadata tracking service. It provides a unified, queryable registry of entities, their fields, and the relationships between them — so that downstream systems, analysis pipelines, and data portals can reliably locate and filter metadata without manually managing spreadsheets or bespoke file manifests.

Hippo is **domain-agnostic**: the entity types, fields, and relationships it tracks are defined entirely by a schema config file authored for each deployment. For example, an omics research deployment might define entity types like Subject, Sample, and Datafile, while a manufacturing deployment might define Batch, Component, and Inspection.

## Key Features

- **Config-driven data model** — Define entity types, fields, and relationships in YAML/JSON schema (Hippo DSL) compiled to LinkML
- **Graph-shaped API** — Query entities and traverse relationships through a relational store with graph semantics
- **Provenance tracking** — Every change is logged with structured context and full audit trail
- **SDK-first architecture** — Embed Hippo directly in Python scripts or notebooks; REST API is a thin transport wrapper
- **Flexible deployment** — From a single researcher's laptop (SQLite) to enterprise cloud (PostgreSQL)

## Related Components

- [Cappella](../cappella/index.md) — Harmonizes data from external sources and upserts into Hippo
- [Canon](../canon/index.md) — Resolves computational artifacts registered in Hippo
- [Aperture](../aperture/index.md) — User-facing CLI and web interface for browsing Hippo entities
- [Bridge](../bridge/index.md) — Adds authentication and unified API gateway for multi-user deployments

## User Documentation

- [Introduction](user-docs/introduction.md) — Detailed overview and use cases
- [Installation](user-docs/installation.md) — Setup instructions
- [Quick Start](user-docs/quickstart.md) — Get running in minutes
- [Schema Guide](user-docs/schema-guide.md) — Authoring entity schemas with Hippo DSL
- [Data Model](user-docs/data-model.md) — Core data model concepts
- [Configuration](user-docs/configuration.md) — Configuration reference
- [CLI Reference](user-docs/cli-reference.md) — Command-line interface
- [API Reference](user-docs/api-reference.md) — REST API endpoints

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [Data Model](design/sec3_data_model.md)
- [Relational Storage Mapping](design/sec3b_relational_storage.md)
- [API Layer](design/sec4_api_layer.md)
- [Ingestion & Integration](design/sec5_ingestion.md)
- [Provenance & Audit](design/sec6_provenance.md)
- [Non-Functional Requirements](design/sec7_nfr.md)
- [Auth Integration](design/sec8_auth_integration.md)
- [Appendix A: Example Schema (Omics)](design/appendix_a_example_schema_omics.md)
- [Appendix B: Implementation Guide](design/appendix_b_implementation_guide.md)
- [Reference: hippo.yaml Config](design/reference_hippo_yaml.md)
- [Reference: validators.yaml](design/reference_validators_yaml.md)
- [Reference: CEL Context](design/reference_cel_context.md)
