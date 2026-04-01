# Bridge — Integration Middleware

!!! warning "Not Yet Implemented"
    Bridge is in the design specification phase. The v1.0 design ships with API key authentication only; OAuth 2.0 and full RBAC are deferred to v1.1.

Bridge is the **integration middleware** for the BASS platform. It sits between the BASS components — Hippo, Cappella, Canon, Aperture — and provides four cross-cutting services that no single component owns:

1. **Unified API** — A single HTTP gateway that routes requests to the correct component
2. **Authentication & Authorization** — Credential validation, token lifecycle, and role-based access control
3. **Cross-Component Sync** — Coordinated data consistency operations spanning multiple components
4. **Monitoring & Observability** — Centralized request logging, health checks, and performance metrics

Bridge is **optional**. Individual BASS components are fully usable without it — Hippo, Cappella, and Canon each expose their own REST APIs. Bridge adds the authentication and routing layer needed for multi-user, multi-component deployments.

## Related Components

- [Hippo](../hippo/index.md) — Bridge routes and authenticates requests to Hippo's REST API
- [Cappella](../cappella/index.md) — Bridge coordinates cross-component sync with Cappella
- [Aperture](../aperture/index.md) — Aperture delegates auth to Bridge when deployed
- [Canon](../canon/index.md) — Bridge routes artifact resolution requests to Canon

## User Documentation

- [Introduction](user-docs/introduction.md) — Overview of integration middleware
- [Authentication](user-docs/auth.md) — API keys, interactive login, roles, and project scoping
- [Security Model](user-docs/security-model.md) — What Bridge protects and audit trail coverage
- [Admin Guide](user-docs/admin-guide.md) — User management, key rotation, monitoring, and backup

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [Unified API Design](design/sec3_api_unification.md)
- [Authentication & Authorization](design/sec4_auth.md)
- [Cross-Component Sync](design/sec5_sync.md)
- [Non-Functional Requirements](design/sec6_nfr.md)
