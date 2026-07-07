## 2. Architecture

**Document status:** Draft v0.1
**Depends on:** sec1_overview.md, Hippo sec2 (auth middleware stub), Cappella sec2 (architecture)
**Feeds into:** Bridge sec3 (unified API), Bridge sec4 (auth), Bridge sec5 (sync), deployment docs

---

### 2.1 Component Map

Bridge is structured as a single Python service with four distinct subsystems:

```
┌────────────────────────────────────────────────────────────────────────┐
│                           Bridge Service                                │
│                                                                         │
│  ┌──────────────┐   ┌───────────────────────────────────────────────┐  │
│  │  HTTP Server │   │                   Core Subsystems              │  │
│  │  (FastAPI)   │──▶│                                               │  │
│  └──────────────┘   │  ┌──────────────┐   ┌───────────────────────┐│  │
│                     │  │  Auth Engine  │   │     Request Router    ││  │
│  ┌──────────────┐   │  │              │   │                       ││  │
│  │  Admin CLI   │   │  │  - validate  │   │  - path rewrite       ││  │
│  │  (bass-mgr)  │──▶│  │  - issue JWT │   │  - actor injection    ││  │
│  └──────────────┘   │  │  - RBAC check│   │  - response passthru  ││  │
│                     │  └──────────────┘   └───────────────────────┘│  │
│                     │                                               │  │
│                     │  ┌──────────────┐   ┌───────────────────────┐│  │
│                     │  │  Sync Engine │   │   Observability Bus   ││  │
│                     │  │              │   │                       ││  │
│                     │  │  - event sub │   │  - request log        ││  │
│                     │  │  - conflict  │   │  - health probes      ││  │
│                     │  │    resolver  │   │  - metrics emit       ││  │
│                     │  └──────────────┘   └───────────────────────┘│  │
│                     └───────────────────────────────────────────────┘  │
│                                         │                               │
│  ┌──────────────────────────────────────┼─────────────────────────┐    │
│  │                  Storage (Bridge-local)                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐│    │
│  │  │ Token Store  │  │  API Key DB  │  │  Sync Event Log        ││    │
│  │  │ (refresh /   │  │  (hashed     │  │  (cross-component      ││    │
│  │  │  revocation) │  │   keys)      │  │   event history)       ││    │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘│    │
│  └─────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

Bridge maintains a small local SQLite (or PostgreSQL) database for its own state: token
revocation records, API key hashes, and sync event history. It does **not** duplicate DataHelix
entity data — that lives exclusively in Hippo.

---

### 2.2 Request Lifecycle

Every inbound request follows the same pipeline:

```
Client Request
      │
      ▼
┌─────────────┐
│  TLS Termn. │  (at ingress; Bridge may run behind a reverse proxy)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Rate Limit │  Check per-key or per-IP rate limit (configurable)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Auth      │  1. Extract Bearer token or X-Api-Key header
│   Middleware│  2. Validate (JWT signature / API key hash lookup)
│             │  3. Build actor + roles claim set
└──────┬──────┘
       │ (401/403 if invalid)
       ▼
┌─────────────┐
│   RBAC      │  Check role permission for requested operation
│   Enforcer  │  Apply project-scope filter if non-admin role
└──────┬──────┘
       │ (403 if insufficient permissions)
       ▼
┌─────────────┐
│   Router    │  Rewrite path, inject X-DataHelix-Actor / X-DataHelix-Roles headers
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Component  │  Forward request to Hippo / Cappella / Canon
│  Proxy      │  Pass response back unchanged (streaming-safe)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Audit Log  │  Record: actor, method, path, status, latency
└──────┬──────┘
       │
       ▼
    Response
```

Auth and RBAC failures are returned before the component is ever contacted. Components
never receive unauthenticated requests when Bridge is active.

---

### 2.3 Module Layout

```
bridge/
├── src/bridge/
│   ├── __init__.py
│   ├── server.py             # FastAPI app factory; assembles middleware stack
│   ├── config.py             # bridge.yaml loader + dataclass schema
│   ├── middleware/
│   │   ├── auth.py           # Token/key extraction and validation
│   │   ├── rbac.py           # Role and project-scope enforcement
│   │   └── rate_limit.py     # Per-actor and per-IP rate limiting
│   ├── router/
│   │   ├── proxy.py          # httpx-based async reverse proxy
│   │   └── registry.py       # Component endpoint registry (from config)
│   ├── auth/
│   │   ├── jwt_engine.py     # JWT issuance and verification
│   │   ├── api_key.py        # API key create / verify / revoke
│   │   ├── token_store.py    # Refresh token store (SQLite / PostgreSQL)
│   │   └── oauth_client.py   # External OIDC client (auth code + device flow)
│   ├── sync/
│   │   ├── event_bus.py      # In-process event pub/sub
│   │   └── consistency.py    # Cross-component consistency checks
│   └── observability/
│       ├── audit_log.py      # Structured auth/request audit events
│       ├── health.py         # /bridge/health aggregation
│       └── metrics.py        # Prometheus-compatible metrics endpoint
├── tests/
│   ├── unit/
│   └── integration/
├── bridge.yaml               # Default configuration template
└── pyproject.toml
```

---

### 2.4 Component Integration

Bridge integrates with each DataHelix component via its REST API. There is no special
protocol — Bridge proxies standard HTTP and adds headers.

#### 2.4.1 Hippo Integration

| Concern | Mechanism |
|---|---|
| Actor identity | Bridge injects `X-DataHelix-Actor: alice@uni.edu` before forwarding |
| Role enforcement | Bridge injects `X-DataHelix-Roles: analyst,project:lab-a` |
| Auth middleware | Hippo's `AuthMiddleware` ABC implementation reads injected headers instead of validating tokens itself |
| SDK mode | No change — SDK uses string `actor` parameter directly; Bridge is not involved |

Hippo's existing `AuthMiddleware` stub (defined in `hippo/rest/auth.py`) is replaced by a
`BridgeAwareAuthMiddleware` implementation that:
- Reads `X-DataHelix-Actor` from request context (validated upstream by Bridge)
- Rejects the header if the source IP is not in Bridge's internal network
- Falls back to an "anonymous" actor if Bridge is not configured (local dev mode)

#### 2.4.2 Cappella Integration

| Concern | Mechanism |
|---|---|
| Pipeline submission | Bridge validates role ≥ `analyst` before forwarding `POST /cappella/runs` |
| Output registration | Cappella contacts Bridge's service-token endpoint to obtain a short-lived JWT for writing back to Hippo |
| Trigger auth | Webhook and schedule triggers authenticated as `service:cappella-runner` |

#### 2.4.3 Canon Integration

| Concern | Mechanism |
|---|---|
| Artifact resolve | `GET /canon/resolve` requires `viewer` role minimum |
| Artifact produce | `POST /canon/produce` requires `analyst` role minimum |
| Cache eviction | `DELETE /canon/cache/*` requires `admin` role |

#### 2.4.4 Aperture Integration

Aperture (CLI and web portal) talks exclusively to Bridge for all DataHelix data operations.
It does not contact Hippo, Cappella, or Canon directly.

- **CLI:** Uses Device Code flow (`datahelix login`); refreshes tokens automatically.
- **Web portal:** Uses Authorization Code + PKCE; session managed by Aperture's BFF.

---

### 2.5 Bridge-Local Storage

Bridge maintains a small local database for its own operational state. This is distinct
from DataHelix entity data (stored in Hippo).

| Store | Contents | Backend options |
|---|---|---|
| **Token store** | Refresh token hashes, revocation records, token families | SQLite, PostgreSQL |
| **API key store** | Hashed API keys, metadata (label, role, expiry, project scope) | SQLite, PostgreSQL |
| **Sync event log** | Cross-component consistency events, resolution history | SQLite, PostgreSQL |

All Bridge-local storage is initialized via `bass-mgr db init` before first use.

---

### 2.6 Configuration

Bridge is configured entirely via `bridge.yaml`. No environment-specific code branches.

Key configuration sections:

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4                        # uvicorn worker count

components:
  hippo:
    url: http://hippo:8001
    health_path: /hippo/health
  cappella:
    url: http://cappella:8002
    health_path: /cappella/health
  canon:
    url: http://canon:8003
    health_path: /canon/health

auth:
  # See sec4_auth.md for full auth config schema
  mode: api_key                     # api_key | oauth2 | disabled
  ...

rate_limit:
  enabled: true
  per_actor_rps: 50                 # requests/sec per authenticated actor
  per_ip_rps: 10                    # requests/sec for unauthenticated IPs

observability:
  audit_log:
    enabled: true
    backend: file                   # file | postgres | stdout
    path: /var/log/datahelix/audit.jsonl
  metrics:
    enabled: true
    path: /bridge/metrics           # Prometheus scrape endpoint
  health:
    path: /bridge/health
```

---

### 2.7 Auth Middleware Replacement Contract

Components that need to integrate with Bridge implement a small interface:

```python
# bridge/sdk/auth_middleware.py (distributed as part of bridge package)

class BridgeAwareAuthMiddleware(AuthMiddlewareABC):
    """
    Replaces the component's stub AuthMiddleware when Bridge is deployed.
    Reads validated identity from injected headers.
    """

    TRUSTED_NETWORKS: list[str]  # configured from bridge.yaml; e.g. ["10.0.0.0/8"]

    def authenticate(self, request: Request) -> str:
        if not self._is_trusted_source(request.client.host):
            raise AuthenticationError("X-DataHelix-Actor not accepted from untrusted source")
        actor = request.headers.get("X-DataHelix-Actor")
        if not actor:
            raise AuthenticationError("Missing X-DataHelix-Actor header")
        return actor

    def authorize(self, actor: str, operation: str, request: Request) -> bool:
        roles = request.headers.get("X-DataHelix-Roles", "").split(",")
        return self._check_permission(roles, operation)
```

This class is importable from `bridge.sdk.auth_middleware` and is the only Bridge
dependency that components need to accept. It has no auth logic of its own — it trusts
the headers that Bridge has already validated.

---

### 2.8 Open Questions

| Question | Priority | Status |
|---|---|---|
| Should Bridge cache component health responses to avoid thundering-herd on `/bridge/health`? | Low | Open |
| Can the proxy layer be made streaming-safe for large Hippo bulk query responses? | Medium | Open — httpx streaming should handle; needs load testing |
| Should Bridge expose a gRPC endpoint in addition to HTTP for internal component traffic? | Low | Deferred to v1.2 |
