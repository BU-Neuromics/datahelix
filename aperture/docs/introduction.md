# Introduction to Aperture

Aperture is the **interface layer** of the BASS platform. It provides the tools that humans use to interact with Hippo, Cappella, Canon, and Bridge — via a command-line interface, a web-based portal (v0.2), and programmatic API client libraries (v0.2).

## The Core Idea

BASS components expose Python SDKs and REST APIs designed for machine-to-machine communication. Aperture translates these into human-friendly interfaces — tabular output, guided workflows, search, and filtering — without adding business logic of its own.

Aperture is to BASS what `git` CLI + GitHub UI are to Git: a thin, ergonomic surface over a well-defined SDK layer.

## What Aperture Does

**Entity browsing** — List, filter, inspect, and search Hippo entities across all configured entity types. Output in table, JSON, or CSV format.

**Entity management** — Create, update, and change availability of entities via the CLI with validation and confirmation prompts.

**Schema inspection** — Display loaded entity types, field definitions, relationships, and validation rules to understand the data model without reading YAML config files.

**Provenance viewing** — Browse the full change history of any entity — who changed it, when, and what the previous values were.

**Batch ingestion** — Trigger and monitor metadata ingestion from flat files or (in v0.2) external sources via Cappella.

**System status** — Show deployment health: Hippo connectivity, adapter type, entity counts, and schema version.

## What Aperture Does Not Do

- **Store data** — All persistent state lives in Hippo. Aperture is stateless.
- **Run analyses** — Computation is Canon's domain. Aperture displays results but does not produce them.
- **Harmonize data** — That is Cappella's role. Aperture triggers Cappella operations and presents results.
- **Enforce authentication** — Auth is Bridge's domain. When Bridge is deployed, Aperture delegates credential validation to it.
- **Define schemas** — Schema authoring is done in LinkML YAML files. Aperture can display schemas but does not edit them.

## Deployment Modes

Aperture works in two modes, configured via `bass config`:

| Mode | How it works | When to use |
|---|---|---|
| **Local SDK** | Aperture imports the Hippo Python SDK directly and operates on a local database. No server needed. | Single researcher on a laptop |
| **Remote REST** | Aperture connects to a running Hippo REST API (optionally behind Bridge for auth). | Shared team deployment |

The same `bass` CLI commands work in both modes — only the backend connection changes.

## Getting Started

- **[Quick Start](quickstart.md)** — Install Aperture and browse entities in 10 minutes
- **[CLI Reference](cli-reference.md)** — Complete command reference for all `bass` subcommands
