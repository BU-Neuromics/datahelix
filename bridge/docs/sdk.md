# Bridge Python SDK

The Bridge SDK provides a Python client for programmatic access to the DataHelix platform
through Bridge. It handles authentication, key management, and request routing so your
code can work with Hippo, Cappella, and Canon through a single client.

---

## Installation

```bash
pip install bass-bridge
# or
uv add bass-bridge
```

The SDK is included in the `bass-bridge` package alongside the server.

---

## BridgeClient

`BridgeClient` is the primary entry point for SDK access to the DataHelix platform.

### Basic usage

```python
from bridge.sdk import BridgeClient

# Authenticate with an API key
client = BridgeClient(
    url="https://datahelix.your-org.edu",
    api_key="datahelix_live_7f3a8b2c..."
)

# Access Hippo entities through Bridge
samples = client.hippo.list_entities("sample", project="lab-a")

# Submit a Cappella pipeline run
run = client.cappella.submit_run(
    pipeline="csv-ingest",
    inputs={"source": "/data/samples.csv"},
)

# Check platform health
health = client.health()
print(health.status)  # "healthy", "degraded", or "unhealthy"
```

### Constructor parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `url` | `str` | Yes | Bridge base URL (e.g., `https://datahelix.your-org.edu`) |
| `api_key` | `str` | No | API key for authentication (`datahelix_live_...` or `datahelix_test_...`) |
| `token` | `str` | No | JWT access token (for interactive session reuse) |
| `timeout` | `float` | No | Request timeout in seconds (default: 30.0) |
| `verify_ssl` | `bool` | No | Verify TLS certificates (default: `True`) |

Provide either `api_key` or `token`. If neither is provided, the client checks the
`DATAHELIX_API_KEY` environment variable.

### Auth header injection

`BridgeClient` automatically injects the appropriate authentication header on every
request:

- **API key:** Sends `Authorization: Bearer datahelix_live_...`
- **JWT:** Sends `Authorization: Bearer <jwt>`
- **Environment variable:** Reads `DATAHELIX_API_KEY` at construction time

```python
# All three are equivalent:
client = BridgeClient(url=url, api_key="datahelix_live_...")
client = BridgeClient(url=url, token="eyJhbGciOi...")

import os
os.environ["DATAHELIX_API_KEY"] = "datahelix_live_..."
client = BridgeClient(url=url)  # reads DATAHELIX_API_KEY
```

### Token refresh

When using JWT authentication, `BridgeClient` handles token refresh automatically.
If an access token expires mid-session, the client exchanges its refresh token for a
new access token without interrupting the caller.

```python
# Token refresh is transparent — no action needed
client = BridgeClient(url=url, token=access_token, refresh_token=refresh_token)
# Requests continue working after the access token expires
```

---

## Component Access

`BridgeClient` exposes component-specific sub-clients that route through Bridge's
unified API. Each sub-client maps to a component prefix (`/api/v1/hippo/`,
`/api/v1/cappella/`, `/api/v1/canon/`).

### Hippo

```python
# List entities
samples = client.hippo.list_entities("sample", project="lab-a")

# Get a single entity
sample = client.hippo.get_entity("sample", "EXT-001")

# Create an entity
client.hippo.create_entity("sample", {
    "external_id": "EXT-002",
    "project": "lab-a",
    "tissue_type": "DLPFC",
})

# Update an entity
client.hippo.update_entity("sample", "EXT-002", {"tissue_type": "cerebellum"})

# Bulk operations
client.hippo.bulk_create("sample", entities=[...])
```

### Cappella

```python
# Submit a pipeline run
run = client.cappella.submit_run(
    pipeline="csv-ingest",
    inputs={"source": "/data/batch.csv"},
)

# Check run status
status = client.cappella.get_run(run.id)
print(status.state)  # "running", "completed", "failed"

# List runs
runs = client.cappella.list_runs(pipeline="csv-ingest", limit=10)
```

### Canon

```python
# Resolve an artifact
artifact = client.canon.resolve("sample", "EXT-001", artifact_type="fastq")

# Produce an artifact
client.canon.produce("sample", "EXT-001", {
    "artifact_type": "fastq",
    "path": "/data/EXT-001.fastq.gz",
})
```

### Raw requests

For endpoints not covered by the sub-clients, use the generic request methods:

```python
# GET request through Bridge
response = client.get("/api/v1/hippo/entities/sample", params={"project": "lab-a"})

# POST request through Bridge
response = client.post("/api/v1/cappella/runs", json={...})
```

These methods apply the same auth header injection and error handling as the
sub-clients.

---

## API Key Management

`BridgeClient` includes methods for managing API keys programmatically. These mirror
the `datahelix auth` CLI commands.

### Create a key

```python
key = client.auth.create_key(
    label="Pipeline runner",
    role="analyst",
    project="lab-a",           # optional: restrict to a project
    expires="2027-01-01",      # optional: set expiry date
)
print(key.secret)   # datahelix_live_... (shown once)
print(key.id)       # key_01jx...
```

The `secret` field is only available in the creation response. Store it immediately.

### List keys

```python
# List your own keys
my_keys = client.auth.list_keys()

# Admin: list all keys
all_keys = client.auth.list_keys(all_users=True)

# Filter by user
user_keys = client.auth.list_keys(user="alice@uni.edu")
```

### Revoke a key

```python
client.auth.revoke_key("key_01jx...", reason="No longer needed")
```

### Rotate a key

Rotation creates a new key and revokes the old one atomically.

```python
new_key = client.auth.rotate_key("key_01jx...")
print(new_key.secret)  # new datahelix_live_... value
```

---

## Health and Diagnostics

### Platform health

```python
health = client.health()

print(health.status)          # "healthy", "degraded", "unhealthy"
print(health.bridge)          # "healthy"
print(health.components)      # {"hippo": {...}, "cappella": {...}, "canon": {...}}
```

### Actor identity

```python
# Check who the current credential resolves to
whoami = client.auth.whoami()
print(whoami.actor)   # "alice@uni.edu"
print(whoami.roles)   # ["analyst"]
```

---

## Error Handling

Bridge errors are raised as `BridgeError` exceptions with structured details:

```python
from bridge.sdk import BridgeClient, BridgeError

client = BridgeClient(url=url, api_key="datahelix_live_...")

try:
    client.hippo.get_entity("sample", "NONEXISTENT")
except BridgeError as e:
    print(e.status_code)   # 404
    print(e.error_code)    # "not_found" (from component) or "component_unavailable"
    print(e.message)       # human-readable description
    print(e.request_id)    # matches X-DataHelix-Request-Id for debugging
```

Bridge-specific error codes (returned before the request reaches a component):

| Error code | HTTP status | Meaning |
|---|---|---|
| `missing_token` | 401 | No credential provided |
| `invalid_token` | 401 | Credential is malformed or signature invalid |
| `expired_token` | 401 | Credential has expired |
| `revoked_token` | 401 | Credential has been revoked |
| `insufficient_role` | 403 | Role does not permit this operation |
| `project_scope_denied` | 403 | Actor is not a member of the target project |
| `rate_limit_exceeded` | 429 | Too many requests |
| `component_unavailable` | 503 | Upstream component is unreachable |

---

## Configuration via Environment Variables

`BridgeClient` reads from these environment variables when explicit parameters are
not provided:

| Variable | Purpose |
|---|---|
| `DATAHELIX_API_KEY` | API key for authentication |
| `DATAHELIX_BRIDGE_URL` | Bridge base URL |
| `DATAHELIX_VERIFY_SSL` | Set to `0` or `false` to disable TLS verification (dev only) |

```python
# With env vars set, no constructor arguments needed:
import os
os.environ["DATAHELIX_BRIDGE_URL"] = "https://datahelix.your-org.edu"
os.environ["DATAHELIX_API_KEY"] = "datahelix_live_..."

client = BridgeClient()
```

---

## Async Support

`BridgeClient` provides an async variant for use in async applications:

```python
from bridge.sdk import AsyncBridgeClient

async def main():
    client = AsyncBridgeClient(url=url, api_key="datahelix_live_...")
    samples = await client.hippo.list_entities("sample")
    await client.close()
```

The async client has the same interface as the synchronous client, with all methods
returning coroutines.
