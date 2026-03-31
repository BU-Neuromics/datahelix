# Bridge — Integration Middleware
## Specification Index

**Codename:** Bridge
**Component:** Integration Middleware
**Version:** Draft v0.1

---

## Document Map

| File | Section | Status | Notes |
|---|---|---|---|
| `sec1_overview.md` | 1. Overview & Scope | ✅ Draft v0.1 | What Bridge is, design philosophy, platform position, deployment topologies |
| `sec2_architecture.md` | 2. Architecture | ✅ Draft v0.1 | Component map, request lifecycle, module layout, component integration contracts |
| `sec3_api_unification.md` | 3. Unified API Design | ✅ Draft v0.1 | URL namespace, routing rules, error format, versioning, CORS, health aggregation |
| `sec4_auth.md` | 4. Authentication & Authorization | ✅ Draft v0.1 | OAuth 2.0 + JWT, flat RBAC, API keys, Hippo provenance integration |
| `sec5_sync.md` | 5. Cross-Component Sync | ✅ Draft v0.1 | Event-driven consistency model, mismatch detection/repair, sync event log |
| `sec6_nfr.md` | 6. Non-Functional Requirements | ✅ Draft v0.1 | Performance targets, availability, security, scalability, observability |

---

## User-Facing Docs

| File | Status | Notes |
|---|---|---|
| `docs/introduction.md` | Stub | Top-level intro |
| `docs/auth.md` | ✅ Draft v0.1 | API keys, interactive login, roles, project scoping, best practices |
| `docs/security-model.md` | ✅ Draft v0.1 | What Bridge protects, audit trail coverage, JWT/key security properties |
| `docs/admin-guide.md` | ✅ Draft v0.1 | User/key mgmt, project mgmt, audit log, key rotation, monitoring, backup |

---

## Key Decisions

| Decision | Rationale |
|---|---|
| **v1.0 ships with API key auth only** | Simplifies Phase 3 significantly; OAuth 2.0/RBAC deferred to v1.1 |
| **Components are auth-unaware by design** | Keeps component code simple and testable without Bridge; auth enforced at transport boundary only |
| **Bridge is a thin gateway, not a microservices orchestrator** | Business logic stays in components; Bridge adds routing, auth, and observability only |
| **SDK bypass is intentional** | Local single-user use (no Bridge) should be frictionless |
| **Flat RBAC in v0.1** | Five predefined roles cover the common academic deployment cases; hierarchy deferred to v0.2 |
| **In-process event bus for sync (v0.1)** | Sufficient for single-server deployments; persistent queue deferred to v1.1 |
| **Is Bridge required?** | **No.** Bridge is optional. Individual components work without it. Multi-user deployments add Bridge for auth and routing. |
| **Bridge API surface** | Bridge exposes both its own auth endpoints (`/api/v1/bridge/`) and proxied component endpoints (`/api/v1/hippo/`, etc.) |

---

## Open Questions

| Question | Priority | Section |
|---|---|---|
| Should Bridge support WebSocket proxying for real-time Cappella run status? | Medium | sec1 |
| Auto-resubmit for sync mismatches — require approval step for non-idempotent pipelines? | High | sec5 |
| How should sync checks handle a temporarily unreachable component (retry vs. skip)? | High | sec5 |
| Audit log retention policy — minimum retention periods, rotation responsibility? | High | sec6 |
| Should Bridge support zero-downtime config reload via SIGHUP? | Medium | sec6 |
| LDAP direct support — current position: no; use OIDC proxy | Medium | sec4 |
| Multi-tenant token store isolation model | High | sec4 |

---

> All six design spec sections at Draft v0.1. User-facing docs (auth, security model, admin guide) also at Draft v0.1. Ready for engineering review.
