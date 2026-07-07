## 1. Overview & Scope

**Document status:** Draft v0.1
**Depends on:** Hippo sec1 (platform position), Cappella sec1 (component overview), Aperture sec1 (user surface)
**Feeds into:** Bridge sec2 (architecture), Bridge sec3 (unified API), Bridge sec4 (auth), all deployment docs

---

### 1.1 What Is Bridge?

Bridge is the **integration middleware** for the DataHelix
platform. It sits between the DataHelix components — Hippo, Cappella, Canon, Aperture — and provides
four cross-cutting services that no single component owns:

1. **Unified API** — A single HTTP gateway that routes requests to the correct component,
   eliminating the need for clients to know each component's address and port.

2. **Authentication & Authorization** — Credential validation, token lifecycle management,
   and role-based access control across all platform endpoints.

3. **Cross-Component Sync** — Coordinated data consistency operations that span more than one
   component (e.g., ensuring Cappella and Hippo agree on entity state after an ingest run).

4. **Monitoring & Observability** — Centralized request logging, health checks, and performance
   metrics for the platform as a whole.

Bridge is **optional**. Individual DataHelix components are fully usable without it:

- Hippo, Cappella, and Canon each expose their own REST APIs when deployed as services.
- Bridge adds the authentication and routing layer needed for multi-user, multi-component
  deployments.
- Single-component or SDK-mode deployments have no need for Bridge.

---

### 1.2 Design Philosophy

#### 1.2.1 Thin Gateway, Not a Microservices Orchestrator

Bridge is a routing and enforcement layer, not a business logic layer. It does not:
- Maintain its own data store for DataHelix entities (that is Hippo's domain)
- Implement pipeline logic or transformation rules (that is Cappella's and Canon's domain)
- Generate analysis outputs (that is Composer's domain)

Bridge is as thin as possible: validate credentials, route requests, inject actor identity,
record auth events. Every other concern belongs in the component it touches.

#### 1.2.2 Auth-Unaware Components by Design

Individual components (Hippo, Cappella, Canon) do not implement credential validation.
They accept a verified `actor` identity injected by Bridge and trust it unconditionally.
This keeps component code simple and testable without Bridge. The full auth design is in
[sec4_auth.md](sec4_auth.md).

#### 1.2.3 SDK Bypass is Intentional

When DataHelix components are used in SDK mode (e.g., a researcher's laptop with `HippoClient`
and SQLite), there is no Bridge and no auth. This is correct. Bridge applies only at the
HTTP transport boundary. Single-user local use should be frictionless.

#### 1.2.4 Progressive Deployment

Bridge is designed to be added to an existing single-component deployment without changing
how that component works internally. A team using Hippo alone can adopt Bridge to add
multi-user access control without modifying Hippo configuration beyond pointing it at
Bridge's network address.

---

### 1.3 Position in the DataHelix Platform

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            DataHelix Platform                                  │
│                                                                           │
│   ┌───────────┐    ┌──────────────────────────────────────────────────┐  │
│   │  Aperture │    │                     Bridge                        │  │
│   │  (CLI /   │───▶│   ┌─────────┐   ┌──────────┐   ┌─────────────┐  │  │
│   │   Web UI) │    │   │  Auth   │   │  Router  │   │  Sync / Mon │  │  │
│   └───────────┘    │   └────┬────┘   └─────┬────┘   └──────┬──────┘  │  │
│                    │        │               │                │          │  │
│                    └────────┴───────────────┴────────────────┴─────────┘  │
│                                      │                                    │
│                    ┌─────────────────┼──────────────────┐                 │
│                    │                 │                   │                 │
│              ┌─────▼──────┐  ┌──────▼──────┐  ┌────────▼───────┐        │
│              │    Hippo   │  │   Cappella  │  │     Canon      │        │
│              │  (metadata)│  │  (harmony)  │  │  (file cache)  │        │
│              └────────────┘  └─────────────┘  └────────────────┘        │
└──────────────────────────────────────────────────────────────────────────┘
```

Bridge is the only component that an external client (Aperture, a notebook, a pipeline
agent) communicates with after initial deployment. Components are not exposed directly in
multi-user deployments.

---

### 1.4 Scope — What Bridge Does and Does Not Do

#### In scope

| Capability | Description |
|---|---|
| API routing | Forward requests to the correct component; handle path rewriting |
| Authentication | Validate API keys and JWTs; issue tokens for browser/CLI flows |
| Authorization | Enforce RBAC role and project-scope rules before forwarding |
| Actor injection | Insert validated actor identity into forwarded requests |
| Service mesh | Route service-to-service traffic between components |
| Health checks | Aggregate per-component health into a platform health endpoint |
| Request logging | Record auth events, response codes, and latency per endpoint |

#### Out of scope

| Capability | Reason |
|---|---|
| Business logic | Belongs in components |
| Data transformation | Belongs in Canon / Cappella |
| File storage | Belongs in Canon / external storage |
| Schema management | Belongs in Hippo |
| Pipeline scheduling | Belongs in Cappella |
| Web UI serving | Belongs in Aperture |
| Full OIDC Identity Provider | Bridge is an OAuth *client*, not an IdP |

---

### 1.5 Deployment Topology

Bridge is deployed as a single Python service alongside the component services it routes.

#### Minimal deployment (single-server)

```
localhost:8000  →  Bridge
localhost:8001  →  Hippo REST API
localhost:8002  →  Cappella REST API
localhost:8003  →  Canon REST API
```

Bridge is the only port exposed to the network. Component ports are internal.

#### Docker Compose (typical team deployment)

All components run in a Docker network. Bridge is the sole `ports:` entry; component
services use `expose:` (internal only). Deployed with a single `docker compose up`.

#### Kubernetes (enterprise)

Bridge runs as a `Service` with an `Ingress` or `LoadBalancer`. Components are `ClusterIP`
services. TLS termination at the ingress. Horizontal scaling is possible for Bridge;
components scale independently.

---

### 1.6 Versioning and Compatibility

Bridge tracks the platform release version (`datahelix-platform`). Component API versions are
managed by each component. Bridge does not impose a version contract on components beyond
requiring that the routed paths respond to HTTP.

Breaking changes to Bridge's own routing or auth API follow the platform versioning policy
documented in `platform/versioning.md`.

---

### 1.7 Open Questions

| Question | Priority | Status |
|---|---|---|
| Should Bridge support WebSocket proxying (e.g., for real-time Cappella run status)? | Medium | Open |
| Plugin model for custom auth providers (e.g., institutional API gateway integration)? | Low | Open |
| Should Bridge expose a GraphQL gateway in addition to REST proxying? | Low | Deferred to v1.2 |
