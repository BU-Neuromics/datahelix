# Introduction to Bridge

Bridge is the **integration middleware** for the BASS platform. It provides four cross-cutting services that no single component owns: a unified API gateway, authentication and authorization, cross-component data synchronization, and centralized monitoring.

## The Core Idea

Each BASS component (Hippo, Cappella, Canon) exposes its own REST API and can be used independently. This works well for single-user or single-component deployments. But when a team runs multiple components together and needs access control, they face several problems:

- Clients must know the address and port of each component separately
- There is no authentication — anyone with network access can read and write data
- There is no centralized audit trail of who did what across components
- Cross-component operations (e.g., ensuring Cappella and Hippo agree after an ingest) have no coordinator

Bridge solves all four by sitting in front of the BASS components as a thin gateway.

## What Bridge Does

**Unified API** — A single HTTP endpoint routes requests to the correct component. Clients call `bridge.example.com/hippo/...` or `bridge.example.com/cappella/...` without managing separate URLs.

**Authentication & Authorization** — Bridge validates API keys (v1.0) or JWTs, checks role-based access control rules, and injects a verified `actor` identity into requests forwarded to components. Components trust this identity without implementing their own credential validation.

**Cross-Component Sync** — Bridge coordinates operations that span multiple components, ensuring data consistency after complex workflows like multi-source ingestion.

**Monitoring & Observability** — Centralized request logging, health checks, and Prometheus metrics for the platform as a whole.

## What Bridge Does Not Do

- **Store BASS data** — All entity data lives in Hippo. Bridge stores only credentials, roles, and audit events.
- **Implement business logic** — Harmonization is Cappella's domain, artifact resolution is Canon's, metadata tracking is Hippo's. Bridge routes and enforces, nothing more.
- **Require deployment** — Bridge is optional. Single-user local deployments work without it. SDK-mode usage bypasses Bridge entirely.

## When Is Bridge Required?

| Deployment | Bridge needed? |
|---|---|
| Single researcher using Hippo SDK on a laptop | No |
| Small team sharing a Hippo REST API on a local server | Optional (adds auth) |
| Multi-component deployment with multiple users | Yes |
| Production platform with audit requirements | Yes |

Bridge can be added to an existing deployment without modifying how components work internally.

## Getting Started

- **[Authentication](auth.md)** — API keys, interactive login, roles, and project scoping
- **[Security Model](security-model.md)** — What Bridge protects and the audit trail it generates
- **[Admin Guide](admin-guide.md)** — Deployment, user management, key rotation, monitoring, and backup
- **[Python SDK](sdk.md)** — `BridgeClient` for programmatic access, key management, and auth header injection
- **[API Reference](api-reference.md)** — All Bridge-owned HTTP endpoints
