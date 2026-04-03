# Aperture — Interface Layer

!!! warning "Not Yet Implemented"
    Aperture is in the design specification phase. The CLI design is fully specified for v0.1; the web UI and API client libraries are deferred to v0.2.

Aperture is the **interface layer** of the BASS platform. It provides the tools that humans use to interact with Hippo, Cappella, Canon, and Bridge — via a command-line interface, a web-based portal, and programmatic API client libraries.

Aperture does not contain business logic. It translates user intent into calls against the underlying BASS component SDKs and APIs, and presents the results in human-readable form. Aperture is to BASS what `git` CLI + GitHub UI are to Git: a thin, ergonomic surface over a well-defined SDK layer.

## Who Is Aperture For?

| Persona | Primary interface | Key workflows |
|---|---|---|
| **Bench scientist** | Web portal (v0.2) | Browse entities, request collections, view provenance, download manifests |
| **Bioinformatician** | CLI + Python SDK | Query entities, trigger ingestion, inspect schemas, script collection requests |
| **Data manager** | CLI + Web portal | Bulk ingest metadata, monitor reconciliation, review audit trails |
| **Platform admin** | CLI | Check system status, validate schemas, manage configuration |

## When to Use Aperture

Use Aperture when you need to:

- **Browse and search** Hippo entities from the command line or (in v0.2) a web browser
- **Create and update** entities interactively, with guided workflows and validation
- **Inspect schemas** — see what entity types, fields, relationships, and validation rules are loaded
- **Trigger ingestion** — load metadata from flat files or external sources
- **View provenance** — see the full change history of any entity

Aperture works **with or without** other BASS components. A researcher using only Hippo on their laptop uses the `bass` CLI. A team running the full platform uses the same CLI plus the web portal with Bridge for authentication.

## Key Features

- **CLI-first** — Typer-based CLI (`bass` command) with auto-completion and `--format table|json|csv` output
- **Entity browsing** — List, filter, inspect, and search Hippo entities
- **Entity management** — Create, update, and change availability of entities
- **Provenance viewing** — Browse entity history and provenance events
- **Ingestion** — Trigger and monitor batch ingestion jobs
- **Schema inspection** — Display loaded schema, entity types, fields, and validation rules
- **System status** — Show deployment health: component connectivity, adapter types, entity counts

!!! warning "Not Yet Implemented"
    The following features are planned for v0.2 and are not yet available:

    - **Web portal** — Browser-based entity browsing and management
    - **API client libraries** — Python and R client packages
    - **Cappella/Canon/Bridge integration** — Cross-component operations via CLI

## Key Concepts

| Concept | Description |
|---|---|
| **`bass` CLI** | The primary command-line tool. Wraps Hippo SDK (local mode) or Hippo REST API (remote mode). |
| **Output formats** | All commands support `--format table\|json\|csv` for scripting and human readability. |
| **Local vs. remote mode** | Configure Aperture to use Hippo's Python SDK directly (no server needed) or point at a remote REST endpoint. |
| **Stateless** | Aperture stores no persistent state. All data lives in Hippo. |

## Getting Started

```bash
pip install bass-aperture
bass config set hippo.url http://localhost:8000  # or use local SDK mode
bass entity list Subject
bass schema show Subject
```

See the **[Quick Start guide](docs/quickstart.md)** for a 10-minute walkthrough covering entity browsing, creation, search, and provenance viewing.

## Related Components

- [Hippo](../hippo/index.md) — Primary data source for entity browsing and management (v0.1)
- [Cappella](../cappella/index.md) — Collection requests and ingestion triggers (v0.2)
- [Canon](../canon/index.md) — Artifact resolution display (v0.2)
- [Bridge](../bridge/index.md) — Authentication delegation for multi-user deployments (v0.2)

## User Documentation

- [Introduction](docs/introduction.md) — Overview of the interface layer
- [Quick Start](docs/quickstart.md) — Get started with the Aperture CLI
- [CLI Reference](docs/cli-reference.md) — Command reference

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [CLI Design](design/sec3_cli.md)
- [Web Interface](design/sec4_web_ui.md) *(v0.2 stub)*
- [API Client Libraries](design/sec5_api_clients.md) *(v0.2 stub)*
- [Non-Functional Requirements](design/sec6_nfr.md)
