# Aperture — Interface Layer

!!! warning "Not Yet Implemented"
    Aperture is in the design specification phase. The CLI design is fully specified for v0.1; the web UI and API client libraries are deferred to v0.2.

Aperture is the **interface layer** of the BASS platform. It provides the tools that humans use to interact with Hippo, Cappella, Canon, and Bridge — via a command-line interface, a web-based portal, and programmatic API client libraries.

Aperture does not contain business logic. It translates user intent into calls against the underlying BASS component SDKs and APIs, and presents the results in human-readable form. Aperture is to BASS what `git` CLI + GitHub UI are to Git: a thin, ergonomic surface over a well-defined SDK layer.

## Key Features

- **CLI-first** — Typer-based CLI (`bass` command) with auto-completion and `--format table|json|csv` output
- **Entity browsing** — List, filter, inspect, and search Hippo entities
- **Ingestion** — Trigger and monitor batch ingestion jobs
- **Schema inspection** — Display loaded schema, entity types, fields, and validation rules

!!! warning "Not Yet Implemented"
    The following features are planned for v0.2 and are not yet available:

    - **Web portal** — Browser-based entity browsing and management
    - **API client libraries** — Python and R client packages
    - **Cappella/Canon/Bridge integration** — Cross-component operations via CLI

## Related Components

- [Hippo](../hippo/index.md) — Primary data source for entity browsing and management (v0.1)
- [Cappella](../cappella/index.md) — Collection requests and ingestion triggers (v0.2)
- [Canon](../canon/index.md) — Artifact resolution display (v0.2)
- [Bridge](../bridge/index.md) — Authentication delegation for multi-user deployments (v0.2)

## User Documentation

- [Introduction](user-docs/introduction.md) — Overview of the interface layer
- [Quick Start](user-docs/quickstart.md) — Get started with the Aperture CLI
- [CLI Reference](user-docs/cli-reference.md) — Command reference

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [CLI Design](design/sec3_cli.md)
- [Web Interface](design/sec4_web_ui.md) *(v0.2 stub)*
- [API Client Libraries](design/sec5_api_clients.md) *(v0.2 stub)*
- [Non-Functional Requirements](design/sec6_nfr.md)
