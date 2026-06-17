## 2. Component Responsibilities and Boundaries

**Document status:** Draft v0.1
**Last updated:** 2026-03-31
**Depends on:** sec1_overview.md
**Feeds into:** sec3_integration.md, component design specs (Hippo, Cappella, Canon, Aperture, Bridge)

---

### 2.1 Component Summary

| Component | Role | Optional? | Dependencies |
|---|---|---|---|
| **Hippo** | Structured domain graph (LinkML runtime) | No (platform foundation) | None |
| **Canon** | File artifact resolver | Yes | Hippo (for provenance write-back) |
| **Cappella** | Harmonization and pipeline engine | Yes | Hippo (sole storage backend) |
| **Aperture** | User-facing CLI and web interface | Yes | Hippo, optionally Canon + Cappella |
| **Bridge** | Auth gateway and integration middleware | Yes (required for multi-user) | All components |

---

### 2.2 Hippo — Structured Domain Graph (LinkML Runtime)

#### What Hippo Owns

- **Entity schema** — the canonical definition of entity types (Subject, Sample, Datafile, etc.), their fields, relationships, and validation rules. Defined in `schema.yaml` and `validators.yaml`.
- **Storage backends** — SQLite (development, single-user), PostgreSQL (production, multi-user). Abstracted via `EntityStore` ABC.
- **Provenance log** — immutable record of every entity mutation: actor, timestamp, changed fields, operation type.
- **Ingestion layer** — flat-file ingest CLI, `ExternalSourceAdapter` ABC for external system connectors (implementations live in Cappella), reference loader plugin system.
- **REST API** — HTTP interface to all SDK capabilities. Used by Bridge (proxy) and Aperture (queries).
- **Python SDK** (`HippoClient`) — the authoritative interface for all reads and writes. REST API and all other components go through this SDK.

#### What Hippo Does Not Own

- External system connector implementations (those live in Cappella)
- Field mapping and transformation config (Cappella adapter config)
- Harmonization logic and vocabulary normalization (Cappella)
- Workflow execution (Cappella/Canon)
- User interface (Aperture)
- Authentication and authorization (Bridge)

#### Design Invariant

Hippo is the **single source of truth** for all entity data. No other component maintains
a parallel copy of entity state. All reads and writes go through Hippo.

---

### 2.3 Canon — File Artifact Resolver

#### What Canon Owns

- **Artifact resolution** — given a set of input entities and a resolution rule, determine the canonical path of the output file.
- **Resolution rules** — defined in `canon.yaml`. Rules express how to derive output file paths from input entity fields.
- **CWL execution integration** — Canon can invoke `cwltool` to produce artifacts that don't yet exist at the resolved path.
- **Storage adapters** — local filesystem, S3, HTTPS (read-only), with a plugin system for additional backends.
- **Artifact cache** — tracking of resolved artifact status (found, missing, stale, producing).

#### What Canon Does Not Own

- Entity metadata (that is Hippo's domain)
- File contents or data management (Canon stores paths, not data)
- Pipeline orchestration or trigger logic (Cappella)
- User interface (Aperture)

#### Design Invariant

Canon is **stateless** with respect to entity data. It reads entities from Hippo at
resolution time and does not cache entity state. Provenance events (artifact resolved,
artifact produced) are written back to Hippo.

---

### 2.4 Cappella — Harmonization and Pipeline Engine

#### What Cappella Owns

- **External system adapter implementations** — connectors for STARLIMS, REDCap, HALO, partner systems, CSV flat files.
- **Field mapping and transformation config** — mapping from source system fields to Hippo canonical fields; vocabulary normalization.
- **Trigger engine** — webhook server, cron scheduler, Hippo poll loop, internal event bus. Coordinates when adapters run.
- **Pipeline execution and output ingestion** — invoking CWL-based analysis pipelines (via Canon), capturing outputs and provenance back to Hippo.
- **Reconciliation** — detecting and surfacing inconsistencies between external systems and Hippo entity state.
- **Operational audit logs** — structured run logs per trigger execution (MVP: JSON; future: `SyncRun` entities in Hippo).

#### What Cappella Does Not Own

- Entity storage (Hippo is Cappella's sole persistent backend — Cappella is stateless)
- The `ExternalSourceAdapter` ABC (that interface lives in Hippo)
- File storage or artifact management (Canon)
- User interface (Aperture)
- Authentication (Bridge)

#### Design Invariant

Cappella is **stateless**. All persistent state (entity data, provenance, run history in
the future) lives in Hippo. A Cappella process restart has no data loss. This is
intentional: Cappella is a force multiplier on top of Hippo, not a second source of truth.

---

### 2.5 Aperture — User-Facing Interface

#### What Aperture Owns

- **CLI** (`bass`) — entity CRUD, schema inspection, provenance history, auth commands, system status.
- **Web portal** (v1.1+) — browser-based query and exploration interface (in design; not in v1.0).
- **Python API client library** — a typed SDK for interacting with the BASS REST API from user code (notebooks, scripts).
- **Auth credential management** — `bass login`, `bass logout`, API key environment variable handling.

#### What Aperture Does Not Own

- Business logic (reads and writes go through Hippo SDK or REST API via Bridge)
- Data storage (Hippo)
- Pipeline execution (Cappella / Canon)
- Authentication enforcement (Bridge)

#### Design Invariant

Aperture is a **thin client**. It has no persistent state of its own (beyond user config in
`~/.config/bass/` and cached session tokens in `~/.bass/tokens.json`). All data operations
go through the BASS REST API (via Bridge in multi-user deployments, directly to Hippo in
single-user deployments).

---

### 2.6 Bridge — Auth Gateway and Integration Middleware

#### What Bridge Owns

- **Authentication** — API key validation, JWT issuance and verification, token lifecycle, optional OIDC integration.
- **Authorization** — RBAC role and project-scope enforcement before forwarding requests to components.
- **Request routing** — single `https://bass.your-org.edu/api/v1/` URL namespace that routes to Hippo, Cappella, Canon.
- **Actor identity injection** — inserts validated `X-Bass-Actor` header into every forwarded request.
- **Cross-component sync** — detects and surfaces consistency mismatches between components after pipeline runs.
- **Observability** — aggregated health checks, request audit logging, Prometheus metrics.

#### What Bridge Does Not Own

- Business logic (it is a routing and enforcement layer only)
- Entity data (lives in Hippo)
- Pipeline logic (lives in Cappella / Canon)

#### Design Invariant

Bridge is **optional** for single-user SDK-mode use. A researcher using `HippoClient`
directly on a laptop needs no Bridge. Bridge becomes necessary for multi-user deployments
where credential enforcement and a unified URL are required.

Bridge is also **thin** by design. No business logic lives here. Components continue to
work independently if Bridge is removed; the only loss is centralized auth and routing.

---

### 2.7 Component Responsibility Matrix

| Concern | Hippo | Canon | Cappella | Aperture | Bridge |
|---|---|---|---|---|---|
| Entity CRUD | ✅ owns | | reads | via API | routes |
| Provenance recording | ✅ owns | writes back | writes back | reads | routes |
| File path resolution | | ✅ owns | triggers | queries | routes |
| External system ingestion | defines ABC | | ✅ owns | triggers | routes |
| Trigger/schedule engine | | | ✅ owns | | |
| User CLI | | | | ✅ owns | |
| Authentication | stub only | | | token mgmt | ✅ owns |
| Authorization | stub only | | | | ✅ owns |
| HTTP routing | | | | | ✅ owns |
| Storage (SQLite/PostgreSQL) | ✅ owns | | | | token store only |
| Schema definition | ✅ owns | references | references | displays | |

---

### 2.8 What "SDK-First" Means in Practice

All components expose a Python SDK as their primary interface. REST APIs are generated
from (or are thin wrappers over) the SDK. This has concrete implications:

| Implication | Detail |
|---|---|
| **Parity** | REST and SDK offer the same capabilities. If you can do it in the SDK, you can do it via REST. If you can't do it in the SDK, you can't do it via REST. |
| **No server required for local use** | `HippoClient` with SQLite needs no running server. A researcher on a laptop has full capability without `hippo serve`. |
| **Test against the SDK** | Unit tests run against the SDK directly, not against a live server. Integration tests add the REST layer. |
| **Bridge transparency** | Bridge proxies REST, not SDK. From a component's perspective, Bridge calls look identical to any other REST caller. |

---

### 2.9 Open Questions

| Question | Priority | Status |
|---|---|---|
| Should Canon expose a REST API of its own, or only be consumed via Cappella + Aperture? | Medium | Open — currently Canon has a REST API; decide if Bridge should proxy it directly |
| Cappella `SyncRun` entities in Hippo — schema design and migration from JSON logs | Medium | Deferred to Cappella v0.3 |
| Aperture web portal scope for v1.1 — what does the MVP feature set look like? | Low | Open |
