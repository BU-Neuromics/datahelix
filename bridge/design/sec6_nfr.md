## 6. Non-Functional Requirements

**Document status:** Draft v0.1
**Depends on:** sec2_architecture.md, sec3_api_unification.md, sec4_auth.md, sec5_sync.md
**Feeds into:** Implementation, deployment docs, performance benchmarking plan

---

### 6.1 Performance

#### 6.1.1 Target Workloads

Bridge is designed for **small-to-medium multi-user research deployments**. Performance
targets assume Bridge is the single gateway for all component traffic.

| Workload profile | Concurrent users | Requests/sec | Typical operation |
|---|---|---|---|
| **Small team** | 2–10 | < 20 req/s | Interactive Aperture queries, occasional pipeline runs |
| **Medium lab** | 10–50 | < 100 req/s | Batch ingestion + active Aperture users |
| **Enterprise** | 50+ | 100+ req/s | Kubernetes deployment; horizontal scaling |

#### 6.1.2 Latency Targets

Bridge adds overhead on top of the component's own response time. The target is that
Bridge's routing and auth enforcement cost no more than **15ms p99** on the hot path.

| Operation | Bridge overhead target | Notes |
|---|---|---|
| JWT validation (cached key) | < 2ms p99 | PyJWT signature check; public key cached in memory |
| API key lookup | < 5ms p99 | SQLite indexed lookup by hashed key |
| RBAC check | < 1ms p99 | In-memory role/permission table |
| Request routing + header injection | < 5ms p99 | Path parsing + header write |
| Total Bridge overhead (hot path) | < 15ms p99 | Cumulative; excludes component response time |

**Upstream latency budget:** Bridge adds at most 15ms. If total response latency must stay
under a target, the component is responsible for the remainder.

#### 6.1.3 Health Check Latency

`GET /api/v1/bridge/health` should respond within 200ms. Results are cached with a 5-second
TTL. A cold health check (cache miss) contacts all components in parallel; the response time
is the max of component probe latencies plus Bridge overhead.

#### 6.1.4 Sync Engine Throughput

Post-run consistency checks run asynchronously and must not block the request path.
Full periodic consistency scans run at low priority (configurable: `scan_priority: low`)
and are rate-limited to avoid overwhelming component REST APIs.

---

### 6.2 Availability and Reliability

#### 6.2.1 Availability Target

Bridge itself targets **99.5% monthly uptime** for team-server deployments. This allows for
~3.6 hours of downtime per month for maintenance.

Bridge is a single-process gateway in v0.1. High availability (multiple Bridge instances
behind a load balancer) is supported via Kubernetes deployment but not required for the
target workloads.

#### 6.2.2 Component Unavailability Handling

When a component is unavailable:

- Bridge returns `503 component_unavailable` immediately (no hang).
- Requests that do not require the unavailable component continue to be served normally.
- Bridge health endpoint reflects `degraded` or `unhealthy` status for the affected component.
- Sync events involving the unavailable component are retried with exponential backoff
  (base: 5s, max: 5min, max attempts: 10 before marking stale).

#### 6.2.3 Graceful Shutdown

Bridge supports graceful shutdown: in-flight requests are completed before the process
exits. Drain timeout is configurable (default: 30 seconds). Outstanding sync checks are
checkpointed to the sync event log before shutdown.

#### 6.2.4 Token Store Durability

The token store (refresh tokens, revocation records) uses SQLite in WAL mode with
`synchronous = NORMAL` by default. This matches Hippo's storage durability posture.
Production deployments should use PostgreSQL for the token store.

---

### 6.3 Security

#### 6.3.1 Secrets Management

| Secret | Storage | Notes |
|---|---|---|
| JWT signing key | Env var or file path (`bridge.yaml` reference) | Never logged |
| OIDC client secret | Env var | Never logged |
| API key plaintext | Never stored | Only shown once at creation; Bridge stores the hash |
| Token store password (PostgreSQL) | Env var | Connection string via `${BRIDGE_TOKEN_DB}` |

Bridge never logs credential material. Request logging redacts the `Authorization` header
value.

#### 6.3.2 Network Exposure

- Bridge listens on `0.0.0.0` by default; this should be restricted to the LAN interface
  in team-server deployments.
- Components should be bound to `127.0.0.1` or a private Docker/Kubernetes network;
  their ports should not be exposed externally.
- TLS is expected to be terminated at a reverse proxy (nginx, Caddy, AWS ALB) in front
  of Bridge. Bridge can be configured to terminate TLS directly if needed.

#### 6.3.3 Audit Log Integrity

Audit log entries must not be modifiable or deletable via the Bridge API. The audit log
backend (file, PostgreSQL) should be configured for append-only access in production.
Audit log events include:

- Auth events: login, token refresh, token revocation, API key creation/revocation
- Request events: actor, method, path, response status, latency (for non-200 responses)
- Sync events: mismatch detected, repair attempted, repair outcome

---

### 6.4 Scalability

#### 6.4.1 Horizontal Scaling

Bridge is stateless in the request path (auth state is in the token store, not in memory
of a specific Bridge instance). Multiple Bridge instances can run behind a load balancer
provided they share the same token store and API key database (PostgreSQL).

#### 6.4.2 Token Store Scaling

SQLite is sufficient for deployments with fewer than 50 active users and low token churn.
PostgreSQL is required when:

- Multiple Bridge instances share state
- Token volume exceeds ~1,000 active refresh tokens
- Audit log volume exceeds the capacity of a single append-only file

#### 6.4.3 Rate Limiting Behavior

Rate limiting in v0.1 is per-instance (in-memory). When multiple Bridge instances run
behind a load balancer, the effective rate limit is `per_actor_rps × instance_count`.
Distributed rate limiting (Redis-backed) is deferred to v1.1.

---

### 6.5 Observability

#### 6.5.1 Logging

All Bridge logs are structured JSON, emitted to stdout. Log levels:

| Level | Usage |
|---|---|
| `INFO` | Request accepted, auth OK, sync check completed |
| `WARNING` | Rate limit hit, component slow response, sync mismatch |
| `ERROR` | Component unreachable, token store write failure, sync repair failure |
| `DEBUG` | Detailed JWT claim inspection, routing decisions (disabled in production) |

#### 6.5.2 Metrics

Bridge emits Prometheus-compatible metrics at `GET /api/v1/bridge/metrics`:

| Metric | Type | Description |
|---|---|---|
| `bridge_requests_total` | Counter | Total requests by method, path prefix, status |
| `bridge_request_duration_seconds` | Histogram | Request latency by method, path prefix |
| `bridge_auth_failures_total` | Counter | Auth failures by type (invalid_token, expired, etc.) |
| `bridge_component_health` | Gauge | 1 = healthy, 0 = unhealthy, per component |
| `bridge_sync_mismatches_total` | Counter | Sync mismatches by type |
| `bridge_active_tokens` | Gauge | Active refresh token count |

#### 6.5.3 Health Checks

`GET /api/v1/bridge/health` — JSON response (see sec3 §3.6 for schema).
HTTP status: `200 OK` (healthy/degraded), `503 Service Unavailable` (unhealthy).

Kubernetes liveness probe: `GET /api/v1/bridge/health` with a 5-second timeout.
Kubernetes readiness probe: same endpoint; Bridge is `ready` when all critical components
respond within their SLO.

---

### 6.6 Maintainability

#### 6.6.1 Configuration Validation

Bridge validates `bridge.yaml` on startup and rejects invalid configuration with a
descriptive error. It does not silently use defaults for required fields.

#### 6.6.2 Dependency Constraints

Bridge's Python dependencies are pinned in `pyproject.toml`. The package list is minimal:

| Package | Purpose |
|---|---|
| `fastapi` | HTTP server |
| `uvicorn` | ASGI runner |
| `httpx` | Async HTTP proxy client |
| `pyjwt` | JWT signing and verification |
| `cryptography` | RS256 key handling |
| `sqlalchemy` | ORM for token/key stores |

Bridge does not depend on Hippo, Cappella, or Canon as Python packages.

#### 6.6.3 Test Coverage

Unit test targets:

| Module | Target coverage |
|---|---|
| Auth middleware (JWT, API key) | ≥ 90% |
| RBAC enforcer | ≥ 90% |
| Request router + header injection | ≥ 85% |
| Sync engine consistency checks | ≥ 80% |
| Audit log writer | ≥ 80% |

Integration test requirements:

- Full request lifecycle with real Hippo (SQLite) as upstream
- Auth failure cases: invalid token, expired token, revoked token, insufficient role
- API key create/rotate/revoke lifecycle
- Sync mismatch detection with mocked Cappella run response

---

### 6.7 Deployment

#### 6.7.1 Installation

```bash
pip install datahelix-bridge          # PyPI
# or
uv add datahelix-bridge               # via uv (preferred)
```

#### 6.7.2 Minimum System Requirements

| Resource | Minimum | Recommended (team) |
|---|---|---|
| CPU | 1 core | 2 cores |
| RAM | 256 MB | 512 MB |
| Disk (token/key store) | 100 MB | 1 GB |
| Python | 3.11+ | 3.13 |

#### 6.7.3 Startup Command

```bash
datahelix-bridge serve --config bridge.yaml
# or
uvicorn bridge.server:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 6.7.4 Database Initialization

```bash
datahelix-mgr bridge db init --config bridge.yaml
```

Creates token store and API key tables. Safe to re-run (idempotent).

---

### 6.8 Open Questions

| Question | Priority | Status |
|---|---|---|
| Should Bridge support zero-downtime config reload (SIGHUP) without restart? | Medium | Open |
| Distributed rate limiting via Redis — is it needed before v1.1? | Medium | Open; depends on horizontal scaling adoption speed |
| Audit log retention policy — how long should auth events be kept, and who is responsible for rotation? | High | Open — likely institution-dependent; document recommended minimums |
