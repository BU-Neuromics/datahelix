# DataHelix

DataHelix is a modular, open-source platform for managing bioinformatics metadata, orchestrating analysis workflows, and integrating research data across sources. Each component can be used independently or composed into a complete system.

## Components

| Component | Role | Description |
|-----------|------|-------------|
| **[Hippo](hippo/index.md)** | Structured Domain Graph | LinkML runtime that becomes the typed knowledge graph its schema describes — entities, fields, and relationships; metadata tracking (*where data lives* / *what it describes*) is one application |
| **[Cappella](cappella/index.md)** | Workflow Engine | Harmonization engine that ingests data from multiple sources into a consistent, provenance-rich picture |
| **[Canon](canon/index.md)** | Data Standards | Artifact resolver — determines whether a computational result exists and how to produce it |
| **[Aperture](aperture/index.md)** | Interface Layer | AI-native data & workflow explorer over the domain graph; the config-driven portal is its substrate |
| **[Bridge](bridge/index.md)** | Integration Middleware | Unified API, authentication, cross-component sync, and monitoring for multi-component deployments |

## Architecture

DataHelix follows an **SDK-first** architecture: all business logic lives in Python SDKs, with REST/GraphQL APIs serving as thin transport wrappers. This means you can embed any component directly in your Python code without running a server.

```
┌─────────────────────────────────────────────┐
│                  Aperture                    │
│          CLI · Web UI · API Clients         │
├─────────────┬───────────────┬───────────────┤
│   Hippo     │   Cappella    │    Canon      │
│  Metadata   │  Harmonize    │  Artifacts    │
├─────────────┴───────────────┴───────────────┤
│                  Bridge                      │
│     Auth · Sync · Monitoring · Unified API  │
└─────────────────────────────────────────────┘
```

## Getting Started

New to DataHelix? Start with the [Platform Overview](platform/src/overview.md) for a high-level introduction, then follow the [Getting Started](platform/src/getting-started.md) guide to set up your first deployment.

For individual components, see each component's introduction page linked in the table above.
