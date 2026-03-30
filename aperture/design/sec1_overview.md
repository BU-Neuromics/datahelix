## 1. Overview & Scope

**Depends on:** Hippo sec1 (entity model), Cappella sec1 (harmonized collections), Bridge INDEX (auth model — pending)
**Feeds into:** sec2 (Architecture), sec3 (CLI Design), sec4 (Web Interface)

---

### 1.1 What Is Aperture?

Aperture is the **interface layer** of the BASS platform. It provides the tools that humans use
to interact with Hippo, Cappella, Canon, and (when deployed) Bridge — via a command-line
interface, a web-based portal, and programmatic API client libraries.

Aperture does not contain business logic. It translates user intent into calls against the
underlying BASS component SDKs and APIs, and presents the results in human-readable form.
Aperture is to BASS what `git` CLI + GitHub UI are to Git: a thin, ergonomic surface over
a well-defined SDK layer.

Aperture is designed to be used **with or without** other BASS components. A researcher using
only Hippo on their laptop interacts through Aperture's CLI. A team running the full platform
uses the same CLI plus the web portal backed by Bridge for auth.

### 1.2 Core Responsibilities

| Responsibility | Description |
|---|---|
| **Entity browsing** | List, filter, inspect, and search Hippo entities across all configured entity types |
| **Entity management** | Create, update, and change availability of entities via guided CLI workflows or web forms |
| **Collection requests** | Request harmonized collections from Cappella — specify criteria, review resolved/unresolved results |
| **Ingestion** | Trigger and monitor batch ingestion jobs (flat-file via Hippo, external-source via Cappella) |
| **Schema inspection** | Display loaded schema, entity type definitions, field types, relationships, and validation rules |
| **Provenance viewing** | Browse entity history and provenance events |
| **System status** | Show deployment health: component connectivity, adapter types, entity counts, schema version |

### 1.3 What Aperture Is Not

Aperture explicitly does not:

- **Store data.** All persistent state lives in Hippo. Aperture is stateless (CLI) or
  session-stateful only (web portal).
- **Run analyses or pipelines.** That is Canon (artifact resolution) and Composer (aggregate
  analysis). Aperture displays results but does not compute them.
- **Harmonize or reconcile data.** That is Cappella. Aperture triggers Cappella operations and
  presents the results.
- **Enforce authentication or authorization.** Auth is Bridge's domain. When Bridge is deployed,
  Aperture delegates auth to it. Without Bridge, Aperture operates in unauthenticated mode
  (same as Hippo's v0.1 no-op auth).
- **Define or manage schemas.** Schema authoring is done in Hippo DSL YAML files and applied via
  `hippo validate` / `hippo migrate`. Aperture can display schemas but does not edit them.

### 1.4 User Personas

| Persona | Primary interface | Key workflows |
|---|---|---|
| **Bench scientist** | Web portal | Browse entities, request collections, view provenance, download manifests |
| **Bioinformatician** | CLI + Python SDK | Query entities, trigger ingestion, inspect schemas, script collection requests |
| **Data manager** | CLI + Web portal | Bulk ingest metadata, monitor reconciliation, review audit trails |
| **Platform admin** | CLI | Check system status, validate schemas, manage configuration |

### 1.5 Delivery Scope (v0.1)

Aperture v0.1 targets a **CLI-first** delivery. The web portal is deferred to v0.2.

**In scope for v0.1:**
- CLI tool (`bass` command) wrapping Hippo SDK and Hippo REST API
- Entity CRUD: list, get, create, update, set-availability
- Entity search (leveraging Hippo's fuzzy search)
- Schema inspection: list entity types, show fields, show relationships
- Provenance viewing: entity history
- System status command
- Batch ingestion trigger (delegating to `hippo ingest`)
- Output formatting: table, JSON, CSV
- Configuration: target Hippo instance (local SDK or remote REST URL)

**Deferred to v0.2:**
- Web portal (server-rendered or SPA — decision pending)
- Cappella integration (collection requests, ingestion triggers, reconciliation views)
- Canon integration (artifact resolution status)
- Bridge integration (authenticated sessions, RBAC-aware UI)
- API client libraries (Python, R)
- Notification / watch functionality

**Out of scope:**
- Schema editing or migration (use `hippo` CLI directly)
- Pipeline execution (Canon / Composer)
- Direct database access

### 1.6 Key Design Principles

| Principle | Description |
|---|---|
| **SDK-first consumption** | Aperture calls component SDKs directly when co-located (local mode) or REST APIs when remote. No intermediate abstraction layer in v0.1. |
| **Progressive disclosure** | Simple commands for common tasks (`bass list Sample`), detailed flags for power users (`bass list Sample --filter tissue=DLPFC --format json`). |
| **Component-optional** | Each BASS component integration is optional. Aperture gracefully degrades when a component is unavailable — e.g., Cappella commands are hidden if no Cappella endpoint is configured. |
| **Consistent output** | All commands support `--format table|json|csv` for scriptability. Table is default for interactive use; JSON for piping. |
| **Auth-transparent** | When Bridge is configured, auth tokens are acquired and refreshed automatically. The user experience is the same whether auth is on or off. |
| **Local-first** | Zero infrastructure required. `pip install bass-aperture` + a local Hippo instance = working CLI. |

### 1.7 Relationship to Other Components

```
┌──────────────────────────────────────────────────────────────┐
│  Aperture                                                     │
│  CLI (`bass` command) │ Web Portal (v0.2) │ Client Libs (v0.2)│
│                                                               │
│  Translates user intent → SDK / REST calls                   │
├────────────┬────────────┬────────────┬───────────────────────┤
│  Hippo     │  Cappella  │  Canon     │  Bridge (optional)    │
│  Entity    │  Collection│  Artifact  │  Auth, unified API    │
│  CRUD,     │  resolution│  status    │  gateway              │
│  search,   │  ingestion │  (v0.2)    │  (v0.2)               │
│  provenance│  (v0.2)    │            │                       │
└────────────┴────────────┴────────────┴───────────────────────┘
```

**Hippo** is Aperture's primary backend in v0.1. All entity operations go through HippoClient
(local SDK) or the Hippo REST API (remote mode).

**Cappella** provides collection resolution and external ingestion. Aperture v0.2 will add
commands to request collections (`bass resolve ...`) and trigger Cappella ingestion jobs.

**Canon** provides artifact resolution status. Aperture v0.2 will surface Canon resolution
decisions (REUSE/FETCH/BUILD/FAIL) in collection views.

**Bridge** provides authentication and a unified API gateway. When configured, Aperture routes
all requests through Bridge. When absent, Aperture connects to component APIs directly.

### 1.8 Open Questions

| Question | Priority | Status |
|---|---|---|
| CLI framework: Click vs Typer vs argparse? | High | Open — see sec2 §2.3 |
| Own auth or inherit from Bridge? | High | Leaning inherit — Aperture should not implement its own auth; Bridge provides this |
| Which Hippo/Cappella operations to expose first? | High | Decided — v0.1 is Hippo-only; see §1.5 |
| Web portal: server-rendered (Jinja/HTMX) vs SPA (React/Vue)? | Medium | Deferred to v0.2 |
| Should Aperture ship a Python client library or is HippoClient sufficient? | Low | Deferred — HippoClient is sufficient for v0.1 |

### 1.9 Glossary

| Term | Definition |
|---|---|
| **bass** | The Aperture CLI command. Installed via `pip install bass-aperture`. |
| **Local mode** | Aperture instantiates component SDKs directly (e.g., `HippoClient` with a local config file). No network required. |
| **Remote mode** | Aperture connects to component REST APIs over HTTP. Configured via `bass config set hippo.url http://...`. |
| **Collection** | A harmonized set of resolved entities returned by Cappella. Aperture displays these but does not compute them. |
| **Manifest** | A downloadable file (CSV/JSON) listing entity URIs and metadata from a collection — used by pipelines and notebooks. |

---
