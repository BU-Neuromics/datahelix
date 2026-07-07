# Bridge API Reference

This document lists all Bridge-owned HTTP endpoints. Component endpoints (Hippo,
Cappella, Canon) are proxied through Bridge under their respective prefixes but are
documented in each component's own API reference.

All endpoints are under the `/api/v1/bridge/` prefix.

---

## Authentication Endpoints

### Issue token

```
POST /api/v1/bridge/auth/token
```

Issue an access token. Supports Device Code callback and Client Credentials flows.

**Request body (Client Credentials):**

```json
{
  "grant_type": "client_credentials",
  "client_id": "cappella-engine",
  "client_secret": "..."
}
```

**Request body (Device Code callback):**

```json
{
  "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
  "device_code": "...",
  "client_id": "bass-cli"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_token": "rt_..."
}
```

---

### Refresh token

```
POST /api/v1/bridge/auth/token/refresh
```

Exchange a refresh token for a new access token and refresh token pair.

**Request body:**

```json
{
  "grant_type": "refresh_token",
  "refresh_token": "rt_..."
}
```

**Response (200):** Same shape as token issuance. The old refresh token is
invalidated (rotation).

---

### Revoke token

```
POST /api/v1/bridge/auth/token/revoke
```

Revoke an access token (by `jti`) or a refresh token.

**Request body:**

```json
{
  "token": "rt_...",
  "token_type_hint": "refresh_token"
}
```

**Response (200):**

```json
{
  "revoked": true
}
```

---

### Initiate Device Code flow

```
GET /api/v1/bridge/auth/device
```

Start a Device Code authentication flow for CLI login.

**Response (200):**

```json
{
  "device_code": "...",
  "user_code": "ABCD-1234",
  "verification_uri": "https://idp.uni.edu/device",
  "expires_in": 600,
  "interval": 5
}
```

The CLI displays the `user_code` and `verification_uri`. The user opens the URI in
a browser, enters the code, and authenticates. The CLI polls the token endpoint with
the `device_code` until authentication completes.

---

## API Key Endpoints

### Create API key

```
POST /api/v1/bridge/auth/api-keys
```

Create a new API key. Requires `admin` role, or `project_lead`/`analyst` creating
a key for themselves.

**Request body:**

```json
{
  "label": "My notebook key",
  "role": "analyst",
  "project": "lab-a",
  "expires": "2027-01-01T00:00:00Z"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Human-readable key label |
| `role` | string | Yes | Role to assign (`admin`, `project_lead`, `analyst`, `viewer`, `service`) |
| `project` | string | No | Restrict key to a specific project |
| `expires` | string (ISO 8601) | No | Expiry date; no expiry if omitted |

**Response (201):**

```json
{
  "id": "key_01jx...",
  "label": "My notebook key",
  "secret": "datahelix_live_7f3a8b2c4d5e6f...",
  "role": "analyst",
  "project": "lab-a",
  "expires": "2027-01-01T00:00:00Z",
  "created_at": "2026-08-15T10:00:00Z",
  "created_by": "alice@uni.edu"
}
```

The `secret` field is only returned in the creation response. It cannot be retrieved
after this.

---

### List API keys

```
GET /api/v1/bridge/auth/api-keys
```

List API keys visible to the caller.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `all` | boolean | Admin only: list all users' keys (default: own keys only) |
| `user` | string | Admin only: filter by key owner |

**Response (200):**

```json
{
  "keys": [
    {
      "id": "key_01jx...",
      "label": "My notebook key",
      "role": "analyst",
      "project": "lab-a",
      "expires": "2027-01-01T00:00:00Z",
      "created_at": "2026-08-15T10:00:00Z",
      "last_used_at": "2026-08-20T14:30:00Z",
      "created_by": "alice@uni.edu"
    }
  ]
}
```

Note: `secret` is never included in list responses.

---

### Revoke API key

```
DELETE /api/v1/bridge/auth/api-keys/{keyId}
```

Revoke an API key. The key stops working immediately.

**Request body (optional):**

```json
{
  "reason": "Key exposed in repository"
}
```

**Response (200):**

```json
{
  "id": "key_01jx...",
  "revoked": true,
  "revoked_at": "2026-08-20T15:00:00Z"
}
```

---

### Rotate API key

```
POST /api/v1/bridge/auth/api-keys/{keyId}/rotate
```

Atomically create a new key and revoke the old one. The new key inherits the same
label, role, and project scope.

**Response (200):**

```json
{
  "new_key": {
    "id": "key_01jy...",
    "secret": "datahelix_live_9c8d7e6f...",
    "label": "My notebook key",
    "role": "analyst",
    "project": "lab-a"
  },
  "revoked_key": {
    "id": "key_01jx...",
    "revoked_at": "2026-08-20T15:00:00Z"
  }
}
```

---

## Health and Observability

### Platform health

```
GET /api/v1/bridge/health
```

Returns aggregated health status for Bridge and all registered components.

**Response (200 or 503):**

```json
{
  "status": "healthy",
  "bridge": "healthy",
  "components": {
    "hippo": {
      "status": "healthy",
      "latency_ms": 3,
      "url": "http://hippo:8001"
    },
    "cappella": {
      "status": "healthy",
      "latency_ms": 5,
      "url": "http://cappella:8002"
    },
    "canon": {
      "status": "degraded",
      "latency_ms": 800,
      "url": "http://canon:8003",
      "detail": "slow_response"
    }
  },
  "checked_at": "2026-08-15T10:30:00Z"
}
```

**Status values:**

| Status | HTTP code | Meaning |
|---|---|---|
| `healthy` | 200 | All components responding within SLO |
| `degraded` | 200 | One or more components slow or returning non-5xx errors |
| `unhealthy` | 503 | One or more components unreachable or returning 5xx |

Results are cached with a 5-second TTL.

**No authentication required.** This endpoint is intended for load balancer and
Kubernetes health probes.

---

### Prometheus metrics

```
GET /api/v1/bridge/metrics
```

Returns Prometheus-compatible metrics. Enabled when `observability.metrics.enabled: true`
in `bridge.yaml`.

Key metrics:

| Metric | Type | Description |
|---|---|---|
| `bridge_requests_total` | Counter | Total requests by method, path prefix, status |
| `bridge_request_duration_seconds` | Histogram | Latency by method and path prefix |
| `bridge_auth_failures_total` | Counter | Auth failures by type |
| `bridge_component_health` | Gauge | 1 = healthy, 0 = unhealthy, per component |
| `bridge_sync_mismatches_total` | Counter | Sync mismatches by type |
| `bridge_active_tokens` | Gauge | Active refresh token count |

---

## Sync Endpoints

### List sync events

```
GET /api/v1/bridge/sync/events
```

Query the sync event log for cross-component consistency events.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter by resolution status: `unresolved`, `resolved`, `all` (default: `all`) |
| `limit` | integer | Max results (default: 50, max: 500) |
| `offset` | integer | Pagination offset |

**Response (200):**

```json
{
  "events": [
    {
      "id": "evt_...",
      "event_type": "bridge.sync.mismatch",
      "source": "cappella",
      "source_id": "run_abc123",
      "actor": "service:cappella-runner",
      "details": {
        "missing_entities": [
          {"entity_type": "sample", "external_id": "EXT-099"}
        ]
      },
      "resolved": false,
      "resolved_at": null,
      "created_at": "2026-08-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

Requires `admin` role.

---

### Get sync event

```
GET /api/v1/bridge/sync/events/{eventId}
```

Get details for a specific sync event. Requires `admin` role.

---

### Resolve sync event

```
POST /api/v1/bridge/sync/events/{eventId}/resolve
```

Mark a sync event as resolved. Requires `admin` role.

**Request body:**

```json
{
  "note": "Run was cancelled by user; no repair needed"
}
```

---

### Latest consistency scan

```
GET /api/v1/bridge/sync/scan/latest
```

Get results of the most recent periodic consistency scan. Requires `admin` role.

---

### Trigger consistency scan

```
POST /api/v1/bridge/sync/scan
```

Trigger an on-demand full consistency scan. Requires `admin` role.

**Response (202):**

```json
{
  "scan_id": "scan_...",
  "status": "started",
  "started_at": "2026-08-15T10:30:00Z"
}
```

---

## Proxied Component Endpoints

Bridge forwards requests to component APIs under these prefixes. See each component's
documentation for endpoint details.

| Prefix | Component | Example |
|---|---|---|
| `/api/v1/hippo/` | Hippo (structured domain graph) | `GET /api/v1/hippo/entities/sample` |
| `/api/v1/cappella/` | Cappella (workflow engine) | `POST /api/v1/cappella/runs` |
| `/api/v1/canon/` | Canon (file cache) | `GET /api/v1/canon/resolve` |

Bridge strips the `/api/v1/{component}/` prefix before forwarding. Components receive
requests on their own internal path scheme.

All proxied requests require authentication. Bridge injects `X-DataHelix-Actor`,
`X-DataHelix-Roles`, and `X-DataHelix-Request-Id` headers before forwarding.

---

## Error Format

All Bridge-generated errors use a consistent JSON structure:

```json
{
  "error": "insufficient_role",
  "message": "Role 'viewer' cannot perform 'entity:create'",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {}
}
```

See [Authentication](auth.md) for the full list of Bridge error codes.
