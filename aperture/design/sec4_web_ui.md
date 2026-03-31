## 4. Web Interface

**Depends on:** sec1 (personas, scope decision — web portal deferred to v0.2), sec2 (architecture, backend integration layer)
**Feeds into:** sec5 (API Client Libraries), Implementation (v0.2)

---

> **Status: Deferred to Aperture v0.2**
>
> The web portal is explicitly out of scope for v0.1. This section captures the
> design decisions already made, the open questions that remain, and the
> architectural constraints the v0.1 CLI implementation must not violate in order
> to make the v0.2 web portal straightforward to add.

---

### 4.1 Motivation

The `bass` CLI (v0.1) is sufficient for bioinformaticians and data managers working in terminal
environments. A web portal extends BASS to bench scientists and data consumers who prefer a
browser-based interface for browsing entities, requesting collections, and downloading manifests.

The web portal is not a separate product — it is an additional presentation layer over the
same `backends/` integration layer used by the CLI (see sec2 §2.2). No new business logic is
introduced in the portal.

---

### 4.2 Decisions Made (Binding for v0.1 Implementation)

| Decision | Choice | Rationale |
|---|---|---|
| When to deliver | v0.2 | v0.1 scope is CLI-only; web adds complexity without addressing the primary user (bioinformatician) |
| Portal server vs SPA | **Decision deferred** — see §4.5 | Neither server-rendered (Jinja/HTMX) nor SPA (React/Vue) is ruled out |
| Auth dependency | Bridge required for web portal | A public-facing web UI must have auth; deploying the portal without Bridge is not supported |
| Package structure | `aperture/portal/` directory reserved | `portal/__init__.py` stub exists in v0.1 to reserve the namespace |
| Backend sharing | Portal must use the same `backends/` layer as the CLI | Prevents divergence in entity access patterns |

---

### 4.3 Anticipated Scope (v0.2)

The following capabilities are planned for the v0.2 web portal. This list is **not a
commitment** — it will be revised when the v0.2 spec is written.

**Entity browsing:**
- Filterable, sortable tables for each entity type
- Entity detail view with all fields and relationship links
- Provenance timeline for each entity

**Collection requests (Cappella integration):**
- Form-based collection request builder
- Progress tracking for active collection jobs
- Downloadable manifest (CSV/JSON) on completion

**Ingestion:**
- Drag-and-drop flat file upload for batch ingest
- Real-time progress view (delegating to Hippo IngestionPipeline)
- Error report download for failed rows

**System:**
- Dashboard: entity counts, recent activity, system health
- Schema browser

---

### 4.4 Architectural Constraints for v0.1

The following constraints must be observed in the v0.1 CLI implementation to ensure the web
portal can be added in v0.2 without restructuring:

1. **`backends/` layer must be transport-agnostic.** `HippoSdkBackend` and `HippoRestBackend`
   must not import or depend on any CLI-specific code (Typer, Rich, stdout). They are plain
   Python classes that can be instantiated from both a CLI command and a web request handler.

2. **No CLI-specific state in backends.** Backends must be stateless or configuration-stateful
   only (holding a URL or SDK client). Session state (auth tokens) will be managed by the
   portal layer in v0.2.

3. **`aperture/portal/` namespace is reserved.** Do not place non-portal code in this
   directory. It exists as an empty package stub (`__init__.py`) only.

4. **`OutputFormatter` must not be called from backends.** Formatting is a presentation-layer
   concern. Backends return plain Python dicts/lists. The CLI layer calls `OutputFormatter`;
   the portal will call its own template/serialization layer.

---

### 4.5 Open Questions (for v0.2 Spec)

| Question | Priority | Notes |
|---|---|---|
| Server-rendered (Jinja2 + HTMX) vs SPA (React/Vue)? | High | Server-rendered is simpler to deploy and maintain; SPA enables richer UX. Decision should follow user research with bench scientists. |
| Standalone portal process or embedded in `bass serve`? | High | A standalone FastAPI + ASGI process is cleanest. Embedding in `hippo serve` would create unwanted coupling. |
| Session management: server-side sessions or JWT-only? | Medium | Depends on Bridge auth model (see Bridge INDEX). |
| Real-time progress (WebSocket vs polling)? | Medium | Ingestion and collection jobs need progress feedback. WebSocket is richer; polling is simpler. |
| Mobile/tablet support? | Low | Bench scientists may use tablets; responsive layout is desirable but not blocking. |

---
