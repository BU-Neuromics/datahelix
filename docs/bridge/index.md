# Bridge — Integration Middleware

!!! warning "Not Yet Implemented"
    Bridge is in the design specification phase. The v1.0 design ships with API key authentication only; OAuth 2.0 and full RBAC are deferred to v1.1.

Bridge is the **integration middleware** for the DataHelix platform. It sits between the DataHelix components — Hippo, Cappella, Canon, Aperture — and provides four cross-cutting services that no single component owns:

1. **Unified API** — A single HTTP gateway that routes requests to the correct component
2. **Authentication & Authorization** — Credential validation, token lifecycle, and role-based access control
3. **Cross-Component Sync** — Coordinated data consistency operations spanning multiple components
4. **Monitoring & Observability** — Centralized request logging, health checks, and performance metrics

Bridge is **optional**. Individual DataHelix components are fully usable without it — Hippo, Cappella, and Canon each expose their own REST APIs. Bridge adds the authentication and routing layer needed for multi-user, multi-component deployments.

## Who Is Bridge For?

- **Platform administrators** who need to control access to DataHelix services with API keys, roles, and project-scoped permissions
- **Teams** deploying multiple DataHelix components that want a single HTTP endpoint instead of managing separate component URLs
- **Security-conscious organizations** that require audit trails, credential rotation, and role-based access control

## When to Use Bridge

Use Bridge when you need:

- **Multi-user access control** — Authenticate users and enforce role-based permissions across all DataHelix components
- **A single API gateway** — Route all requests through one endpoint instead of managing per-component URLs and ports
- **Centralized audit logging** — Track every authenticated request and auth event in one place
- **Cross-component coordination** — Ensure data consistency across Hippo, Cappella, and Canon after complex operations

**When you don't need Bridge:** Single-user local deployments (researcher on a laptop using Hippo SDK directly) require no authentication or routing — Bridge adds no value in this scenario.

## Key Concepts

| Concept | Description |
|---|---|
| **API key** | The primary credential type in v1.0. Keys are scoped to a user and optionally to specific projects. |
| **Role** | Access level assigned to a user: `admin`, `project_lead`, `analyst`, `viewer`, `service`. Each role defines what operations are permitted. |
| **Project scoping** | Keys and permissions can be scoped to specific projects, limiting what data a user can access. |
| **Actor identity** | Bridge validates credentials and injects a verified `actor` identity into requests forwarded to components. Components trust this identity unconditionally. |
| **Auth-unaware components** | Hippo, Cappella, and Canon do not implement credential validation — they rely on Bridge to handle auth at the HTTP boundary. |
| **Progressive deployment** | Bridge can be added to an existing Hippo-only deployment without modifying Hippo's configuration. |

## Architecture Overview

```
┌───────────┐         ┌──────────────────────────────────────┐
│  Aperture │         │                Bridge                 │
│  (CLI /   │────────▶│   Auth  ·  Router  ·  Sync  ·  Mon  │
│   Web UI) │         │     │         │                       │
└───────────┘         │     ▼         ▼                       │
                      │  ┌──────┐ ┌──────┐ ┌──────┐          │
                      │  │Hippo │ │Capp. │ │Canon │          │
                      │  └──────┘ └──────┘ └──────┘          │
                      └──────────────────────────────────────┘
```

Bridge is a thin routing and enforcement layer. It validates credentials, routes requests, injects actor identity, and records auth events. All business logic remains in the components themselves.

## Getting Started

See the **[Authentication guide](docs/auth.md)** for setting up API keys, roles, and project scoping. The **[Admin Guide](docs/admin-guide.md)** covers deployment, user management, key rotation, monitoring, and backup procedures.

## Related Components

- [Mosaic](../mosaic/index.md) — Bridge routes and authenticates requests to Hippo's REST API
- [Cappella](../cappella/index.md) — Bridge coordinates cross-component sync with Cappella
- [Aperture](../aperture/index.md) — Aperture delegates auth to Bridge when deployed
- [Canon](../canon/index.md) — Bridge routes artifact resolution requests to Canon

## User Documentation

- [Introduction](docs/introduction.md) — Overview of integration middleware
- [Authentication](docs/auth.md) — API keys, interactive login, roles, and project scoping
- [Security Model](docs/security-model.md) — What Bridge protects and audit trail coverage
- [Admin Guide](docs/admin-guide.md) — User management, key rotation, monitoring, and backup

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [Unified API Design](design/sec3_api_unification.md)
- [Authentication & Authorization](design/sec4_auth.md)
- [Cross-Component Sync](design/sec5_sync.md)
- [Non-Functional Requirements](design/sec6_nfr.md)
