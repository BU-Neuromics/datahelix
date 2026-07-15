# DataHelix Platform Deployment Guide

Deployment options for the DataHelix platform across local, single-host, and multi-node
environments. Choose the tier that matches your usage:

| Tier | Who it's for | Auth | Storage |
|---|---|---|---|
| **Local (no Docker)** | Single researcher, laptop/workstation | None | SQLite |
| **Single-node (packaged recipe)** | Small team, shared lab server | API keys via Bridge | SQLite or PostgreSQL |
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

## Tier 2: Single-Node (packaged recipe)

Single-node container deployment is packaged as a **recipe** under
[`deploy/recipes/`](../deploy/recipes/), not a hand-maintained compose file. Start with
the **solo** recipe — a single-container bundle (Mosaic + the Aperture portal behind an
nginx same-origin seam) driven by `docker compose`:

```bash
cd deploy/recipes/solo
make init         # scaffold an example project (schemas/ + config)
make up           # build + boot the bundle
# portal + API on http://localhost:8080  (health: GET /health)
make migrate      # apply schema changes on iteration
make down
```

See [`deploy/recipes/solo/README.md`](../deploy/recipes/solo/README.md) for the full loop
(browse, edit schema, migrate-on-restart, verify). The recipe pins the exact
Mosaic/Aperture pair from the certified-frontier ledger (platform
[ADR-0001](design/decisions/ADR-0001-certified-frontier-composition.md)) and is
boot-tested in CI (the `Solo recipe` workflow — on change **and** nightly), so its
config stays in sync with the components' runtime contracts.

> A hand-rolled root `docker-compose.yml` (plus `config/*.yaml`) previously lived at the
> repo root for this tier. It was **removed (2026-07)**: it had drifted out of sync with
> the component config contracts (`MosaicConfig` / `CanonConfig`) and nothing in CI booted
> it, so the drift went unnoticed. Multi-component recipes (e.g. `platform-full`) land under
> `deploy/recipes/` as they are built — see `proposals/deployment-recipes.md`.

---

## Tier 3: Multi-Node (Kubernetes / Helm)

A Helm chart for multi-node production deployment is planned for Phase 4. Until then, use
the single-node recipe (`deploy/recipes/`) on a well-resourced server for team deployments.

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
(`mosaic/design/sec7_nfr.md`, `bridge/design/sec6_nfr.md`).
