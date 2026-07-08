# DataHelix Platform Deployment Guide

Deployment options for the DataHelix platform across local, single-host, and multi-node
environments. Choose the tier that matches your usage:

| Tier | Who it's for | Auth | Storage |
|---|---|---|---|
| **Local (no Docker)** | Single researcher, laptop/workstation | None | SQLite |
| **Single-node (Docker Compose)** | Small team, shared lab server | API keys via Bridge | SQLite or PostgreSQL |
| **Multi-node (Kubernetes/Helm)** | Institutional deployment | OIDC + Bridge | PostgreSQL |

---

## Tier 1: Local Installation (No Docker)

Install each component you need with `pip`. Components are independent — install only what
your workflow requires.

```bash
# Core structured domain graph / LinkML runtime (Mosaic, formerly Hippo,
# ADR-0004; required for all other components)
pip install mosaic

# Artifact resolver (if you use Canon rules + CWL pipelines)
pip install canon cwltool

# Workflow engine (if you use Cappella pipeline adapters)
pip install cappella
```

Initialize Mosaic in a local project directory:

```bash
mosaic init --path ~/DataHelix
cd ~/DataHelix
mosaic serve          # starts REST API on http://localhost:8001
```

No Bridge, no auth, no Docker required. This is the correct setup for single-user local
research.

---

## Tier 2: Single-Node Deployment with Docker Compose

Use this for a shared lab server where multiple team members need authenticated access.
Provides Mosaic + Canon + Cappella + Bridge in a single `docker-compose.yaml`.

### Prerequisites

- Docker 24+ and Docker Compose v2
- A server with at least 4 GB RAM and 20 GB free disk
- A domain name or internal hostname (e.g., `datahelix.lab.internal`)

### Directory Layout

```
DataHelix/
├── docker-compose.yaml
├── config/
│   ├── mosaic.yaml
│   ├── canon.yaml
│   ├── cappella.yaml
│   └── bridge.yaml
├── schemas/
│   └── schema.yaml          # your Mosaic schema
├── data/
│   ├── mosaic-db/           # Mosaic SQLite (or mount PostgreSQL socket)
│   └── canon-outputs/       # Canon workflow output files
└── logs/
```

### `docker-compose.yaml`

```yaml
version: "3.9"

services:

  mosaic:
    image: ghcr.io/datahelix-platform/mosaic:0.4
    volumes:
      - ./config/mosaic.yaml:/app/mosaic.yaml:ro
      - ./schemas:/app/schemas:ro
      - ./data/mosaic-db:/data/mosaic-db
    environment:
      MOSAIC_DB: /data/mosaic-db/mosaic.db
    ports:
      - "8001:8001"          # internal only; Bridge proxies all external traffic
    restart: unless-stopped

  canon:
    image: ghcr.io/datahelix-platform/canon:0.1
    volumes:
      - ./config/canon.yaml:/app/canon.yaml:ro
      - ./data/canon-outputs:/data/outputs
    environment:
      MOSAIC_TOKEN: ${CANON_SERVICE_TOKEN}
    depends_on:
      - mosaic
    restart: unless-stopped

  cappella:
    image: ghcr.io/datahelix-platform/cappella:0.3
    volumes:
      - ./config/cappella.yaml:/app/cappella.yaml:ro
    environment:
      MOSAIC_TOKEN: ${CAPPELLA_SERVICE_TOKEN}
    depends_on:
      - mosaic
    restart: unless-stopped

  bridge:
    image: ghcr.io/datahelix-platform/bridge:0.1
    volumes:
      - ./config/bridge.yaml:/app/bridge.yaml:ro
    environment:
      BRIDGE_JWT_KEY: ${BRIDGE_JWT_KEY}
      BRIDGE_LOCAL_ADMIN_PW: ${BRIDGE_LOCAL_ADMIN_PW}
    ports:
      - "8080:8080"          # public-facing HTTPS termination (add a reverse proxy)
    depends_on:
      - mosaic
      - canon
      - cappella
    restart: unless-stopped
```

### `config/bridge.yaml`

```yaml
components:
  mosaic:    http://mosaic:8001
  canon:    http://canon:8002
  cappella: http://cappella:8003

auth:
  jwt:
    algorithm: HS256                    # RS256 for production
    signing_key: ${BRIDGE_JWT_KEY}
    access_token_ttl: 900
    refresh_token_ttl: 604800
  idp:
    provider: local                     # Replace with oidc for institutional SSO
  local_provider:
    enabled: true
    users:
      - username: admin
        password: ${BRIDGE_LOCAL_ADMIN_PW}
        roles: [admin]
  token_store:
    backend: sqlite
    connection: /data/bridge/tokens.db
  api_key_store:
    backend: sqlite
    connection: /data/bridge/apikeys.db
```

### `config/mosaic.yaml`

```yaml
storage:
  backend: sqlite
  connection: ${MOSAIC_DB}

bridge:
  enabled: true
  trust_proxy:
    - "172.16.0.0/12"      # Docker internal network

schema:
  path: /app/schemas/schema.yaml

log_level: INFO
```

### Environment Variables (`.env`)

Create a `.env` file in the `DataHelix/` directory. **Never commit this file to version control.**

```bash
# .env

BRIDGE_JWT_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
BRIDGE_LOCAL_ADMIN_PW=<strong password>
CANON_SERVICE_TOKEN=<generate with: datahelix-keygen>
CAPPELLA_SERVICE_TOKEN=<generate with: datahelix-keygen>
```

### Start the Stack

```bash
cd DataHelix/
docker compose up -d

# Verify all services are healthy
docker compose ps
```

### First-Time Setup

After the stack is running:

```bash
# Install Canon's reference schema into Mosaic (run once)
docker compose exec mosaic mosaic reference install canon

# Create the first API key for your team
curl -X POST http://localhost:8080/bridge/auth/login \
  -d '{"username": "admin", "password": "<your-admin-pw>"}' \
  | jq '.access_token'

# Use the token to create a long-lived API key for a team member
curl -X POST http://localhost:8080/bridge/auth/api-keys \
  -H "Authorization: Bearer <access-token>" \
  -d '{"label": "alice-workstation", "role": "analyst"}'
```

Team members set `DATAHELIX_API_KEY=datahelix_live_...` in their environment and point their tools at
`http://datahelix.lab.internal:8080`.

---

## Tier 3: Multi-Node (Kubernetes / Helm)

A Helm chart for multi-node production deployment is planned for Phase 4. Until then, use
the Docker Compose tier on a well-resourced server for team deployments.

For PostgreSQL-backed Mosaic (required for multi-user concurrent write loads):

1. Provision a PostgreSQL instance (managed service or self-hosted).
2. Set `storage.backend: postgresql` and `storage.connection: <postgres-dsn>` in
   `mosaic.yaml`.
3. Run `mosaic migrate` on first start to initialize the schema.

PostgreSQL support is the primary enabling technology for the Tier 3 deployment path.
Once the PostgreSQL storage adapter ships (Phase 4 milestone), the Helm chart will follow.

---

## Upgrading

Component images are versioned independently. To upgrade a single component:

```bash
# Pull the new image
docker compose pull mosaic

# Apply schema migrations (if any) before restarting
docker compose run --rm mosaic mosaic migrate

# Restart the service
docker compose up -d mosaic
```

Always run `mosaic migrate` before restarting Mosaic after an upgrade. The migration command
is safe to run on an already-migrated database (it is idempotent).

> **Only deploy certified pairs.** Because components version independently, a pair of
> versions is safe to run together only if the **certified-frontier ledger** has certified
> it (platform [ADR-0001](design/decisions/ADR-0001-certified-frontier-composition.md)).
> Deploy tooling must run the ledger gate as a pre-flight — it refuses any pair (and digest)
> not present as a passing ledger entry, so an untested version skew can never reach
> production:
>
> ```bash
> # pre-flight: exits non-zero unless the pinned pair is certified
> bash certification/scripts/deploy_gate.sh certification/composition.lock.json
> ```
>
> If the pair you need is uncertified, run an on-demand backfill (the "Certify composition"
> workflow via `workflow_dispatch`) and it joins the ledger. Never re-cut a released version
> under the same number — the ledger records digests and a rebuilt artifact is refused.

---

## Backup

**SQLite (single-node):**

```bash
# Daily cron backup
sqlite3 data/mosaic-db/mosaic.db ".backup '/backups/mosaic-$(date +%Y%m%d).db'"
```

The Mosaic provenance log is immutable — a daily backup of the SQLite file is sufficient for
disaster recovery.

**PostgreSQL (multi-node):** Use your standard PostgreSQL backup tooling (`pg_dump`,
continuous WAL archiving, or managed-service snapshots).

---

## Monitoring

Each component exposes a health endpoint:

| Component | Health endpoint |
|---|---|
| Mosaic | `GET /health` |
| Bridge | `GET /bridge/health` |
| Cappella | `GET /health` |

Bridge's health endpoint aggregates the health of all downstream components and returns a
summary suitable for monitoring systems.

For observability beyond health checks, see the NFR sections in each component's design spec
(`hippo/design/sec7_nfr.md`, `bridge/design/sec6_nfr.md`).
