# DataHelix deployment recipes — MVP single-container, IDE, and the scale ladder

**Status:** 🟢 **Settled — ready for Phase 1.** Written 2026-07-14 from a verified survey of the four repos (datahelix, mosaic, aperture, linkml-modeler-app). All §4 questions decided by owner review the same day: Mosaic naming now (catch-up in [#49](https://github.com/BU-Neuromics/datahelix/issues/49)), Modeler first-class in `solo`, bundle certification via the middle path, devcontainer deferred entirely (local development only). Ratification as a platform ADR happens in Phase 3 (§1.11).
**Goal:** Define a small family of named, versioned deployment recipes for the platform — starting with a single-container **MVP** (Aperture + Mosaic, optional LinkML Modeler, SQLite, single-user) and an **IDE** recipe that turns the same stack into a schema-iteration development environment with an incorporated `mosaic migrate` loop.
**Non-goal:** Kubernetes/Helm (Tier 3 in `platform/deployment.md` — stays "Phase 4"); multi-user auth (Bridge is a design + nginx stub, no application layer); replacing the certification stack under `certification/compose/` (it remains the composition-certification harness, not a user-facing recipe).

---

## 0. Current state (verified 2026-07-14)

What each component actually offers a deployment today:

- **Mosaic** (`BU-Neuromics/mosaic`, distributed as `datahelix-mosaic` v0.11.0; the datahelix submodule still points at `BU-Neuromics/hippo` — see open question 4.1):
  - `mosaic serve` exists (FastAPI/uvicorn, default `127.0.0.1:8000`, `--graphql` mounts GraphQL at `/graphql`, `--config` or cwd auto-discovery of `mosaic.yaml`). `GET /health` is unauthenticated.
  - `mosaic migrate` exists and is **SQLite-only, additive/expand-only** (new tables/columns/indexes/FTS), with `--schema-dir` (default `schemas/`) and `--db-path` (default `data/mosaic.db`). It **fails if the DB doesn't exist**. The v0.1 schema-sync model is **restart-on-migrate** (no live reload) — which is exactly the loop the IDE recipe needs.
  - The SQLite adapter creates its file and system tables idempotently (`CREATE TABLE IF NOT EXISTS`, `src/mosaic/core/storage/adapters/sqlite_adapter.py:1079ff`), so a **fresh DB needs no migrate — only an existing DB evolving under a changed schema does**.
  - `mosaic init` scaffolds a project directory (`mosaic.yaml` + template schemas + `data/`). Config is flat pydantic `MosaicConfig` (`schema_path` required; `storage_backend`/`database_url` optional; `${VAR}` env substitution supported; `MOSAIC_*` env vars with legacy `HIPPO_*` fallback).
  - A root `Dockerfile` exists but is **broken as written**: it creates user/group `hippo` yet `chown`s and runs as a nonexistent `datahelix` user. It also EXPOSEs 8001 (CLI default is 8000) and creates `/data/hippo-db` that nothing wires to the SQLite default path.
- **Aperture** (`BU-Neuromics/aperture`): the SPA under `web/` is the deployable artifact — static Vite build served by nginx, **published as a digest-addressed image to `ghcr.io/bu-neuromics/aperture`** (`web/Dockerfile`, `.github/workflows/release.yml`). Per **ADR-0034** the image is deployment-agnostic: `VITE_HIPPO_GRAPHQL_URL`, `VITE_HIPPO_CONTROL_PLANE_URL`, `VITE_WORKFLOWS`, `VITE_NAV` are injected **at container start** into `/config.js`. The SPA talks to Mosaic's GraphQL endpoint **directly from the browser**; capabilities come from live `__schema` introspection, so the UI adapts to whatever schema Mosaic is running. Auth is a no-op (Bridge deferred, ADR-0016); effectively single-user/trusted-network by design. The Python package `datahelix-aperture` is a client library, not a service — it is not part of any recipe.
- **LinkML Modeler** (`BU-Neuromics/linkml-modeler-app`): the web build is a **purely client-side SPA** — file access via the browser File System Access API (user's local disk), git via isomorphic-git into browser IndexedDB. **There is no server-side file API: volume-mounting schemas into its container does not expose them to the app.** The only server pieces are a static server and an optional stateless CORS proxy (`packages/proxy/`, needed only for remote-git operations). Its `deploy/web/` Dockerfile expects a host-built `dist/` (not self-contained), and all its config (`VITE_BASE_URL`, `VITE_GIT_CORS_PROXY`, `VITE_GITHUB_CLIENT_ID`) is **build-time**, unlike Aperture's runtime injection.
- **DataHelix repo**: `platform/deployment.md` defines the three-tier model (local / single-node compose / k8s) and — with platform **ADR-0001** — mandates the certified-frontier **deploy gate** (`certification/scripts/deploy_gate.sh` against `certification/composition.lock.json`) for production deployments of component pairs. Docker artifacts are currently scattered: root `docker-compose.yml` (build-from-source: postgres + hippo + canon + cappella + bridge; diverges from the image-based compose sketched in `deployment.md`) and `certification/compose/docker-compose.certify.yml` (digest-pinned hippo+aperture pair — the closest thing to a canonical container recipe today). There is no consolidated `deploy/` directory and no devcontainer.

Two facts shape everything below:

1. **Aperture and the Modeler are static files; Mosaic is the only long-running process.** A "single container" is therefore realistic: one nginx serving two SPAs and reverse-proxying to one uvicorn.
2. **The Modeler cannot read server volumes.** The schema-iteration loop closes on the **host filesystem** (browser FSAA edits the same directory that is bind-mounted into Mosaic), which works beautifully for a localhost IDE and not at all for a remote deployment — remote schema collaboration is git-based and out of MVP scope.

---

## 1. Decisions (proposed — defaults recommended, none locked)

| # | Question | Proposed decision | Notes |
|---|---|---|---|
| 1.1 | Where do recipes live? | **`datahelix` repo, new `deploy/recipes/<name>/` directory** | Composition is this repo's charter; the deploy gate, composition ledger, and cross-component pins already live here; a recipe by definition spans components so no component repo is the right home. Component repos keep owning their own single-component images (Aperture already does; Mosaic should after the Dockerfile fix). The scattered root `docker-compose.yml` migrates into `deploy/recipes/platform-full/` in a later phase. |
| 1.2 | Recipe family & names | **`solo`** (single-container production MVP), **`ide`** (dev environment / schema workbench), **`team`** (compose: postgres + separate services), **`platform-full`** (existing root compose, relocated later) | A named ladder of scale. `solo` and `ide` are this proposal's deliverables; `team` is specified but can trail; `platform-full` is a relocation, not new work. |
| 1.3 | `solo` shape | **One container, one published port.** nginx front: Aperture SPA at `/`, Modeler at `/modeler/`, reverse-proxy `/graphql` + REST + `/docs` to uvicorn on localhost. `mosaic serve --graphql` on SQLite. | Same-origin proxying sidesteps CORS entirely and means `VITE_HIPPO_GRAPHQL_URL=/graphql` (relative URL — verify once, expected to work since urql accepts relative URLs; fallback is absolute URL injection at start, which ADR-0034 already supports). |
| 1.4 | `solo` image composition | **Build `FROM` the published, digest-pinned component images** — python base with `datahelix-mosaic[graphql]` installed (or `FROM` the fixed Mosaic image) + `COPY --from=ghcr.io/bu-neuromics/aperture@sha256:… /usr/share/nginx/html /srv/aperture` + Modeler dist from a pinned build. | Keeps the bundle honest to ADR-0001: the pair inside the bundle is a ledger-certified pair; the bundle Dockerfile is where the digests are pinned. Never build components from source in a production recipe. |
| 1.5 | `solo` process supervision | **supervisord** (or s6-overlay) running nginx + `mosaic serve`; entrypoint runs the migrate step first (§2.1) | Two processes in one container is a deliberate, documented MVP trade-off; `team` splits them. |
| 1.6 | Storage & state | **One host "project directory" bind-mounted at `/project`**: `mosaic.yaml`, `schemas/`, `data/mosaic.db`. Container workdir = `/project`. | Matches `mosaic init` output 1:1, makes the deployment a git-versionable folder, and is exactly the directory the Modeler edits via FSAA in the IDE flow. Explicit `--db-path /project/data/mosaic.db` — never rely on cwd-relative defaults inside a container. |
| 1.7 | Migrate-on-start policy | Entrypoint: if `data/mosaic.db` exists → `mosaic migrate --schema-dir schemas --db-path data/mosaic.db` (fail-fast on breaking changes, i.e. no `--allow-breaking`); if absent → skip (first boot self-initializes). Then `exec` serve. | Encodes the restart-on-migrate model: "restart the container" = "apply additive schema changes." Breaking changes intentionally stop the boot and point at `mosaic schema safe-deploy`. |
| 1.8 | Modeler inclusion | ✅ **Decided (owner, 2026-07-14): Modeler ships in `solo` by default** — users iterating their own schema is a first-class platform capability, not a dev-only feature. CORS proxy included alongside it (needed for the remote workflow, §2.1a). | Since the Modeler can't reach the server's schema dir (§0 fact 2), including it obligates the recipe to close the schema loop in *both* deployment modes — see the workflow analysis in §2.1a. |
| 1.9 | `ide` shape | **Compose file, not single container** — services: `mosaic` (from source checkout *or* pinned image; `--reload` optional), `aperture` (published image), `modeler` + `cors-proxy` (profile `modeler`), everything bind-mounted from the project dir. Plus a `make migrate` / `docker compose restart mosaic` documented inner loop. | Dev wants independent restarts, logs, and source-mounting; cramming that into one container fights compose for no benefit. The IDE recipe is *allowed* to build from source (gate does not apply — ADR-0001 governs deployment, not development). |
| 1.10 | Deploy gate applicability | `solo` and `team` are **production recipes → deploy-gate pre-flight required** (pinned digests must be a certified pair). `ide` is exempt. The bundled `solo` image itself should eventually enter certification as its own artifact. | Directly per platform ADR-0001 / `platform/deployment.md:258`. |
| 1.11 | Ratification | After discussion, the load-bearing bits (recipe home, image-not-source rule for production recipes, gate applicability) become a **platform ADR** (ADR-0002); this proposal stays as the runbook. | Matches the repo's ADR-first convention. |

---

## 2. The recipes

### 2.1 `deploy/recipes/solo/` — single-container production MVP

**Audience:** one user or one trusted small group; a lab workstation, a single VM. No auth (documented loudly — Bridge is not in this recipe; put it behind a VPN/SSH tunnel or localhost).

```
┌─────────────────────────────── container ───────────────────────────────┐
│  nginx :80                                                               │
│   ├── /            → Aperture SPA (static, from pinned aperture image)   │
│   ├── /modeler/    → LinkML Modeler SPA (static, included by default)    │
│   ├── /cors-proxy/ → proxy → modeler git relay (localhost sidecar)       │
│   ├── /graphql,/entities,/search,… → proxy → uvicorn 127.0.0.1:8001      │
│   └── /docs,/openapi.json          → proxy → uvicorn (FastAPI docs)      │
│  supervisord: nginx + `mosaic serve --graphql --host 127.0.0.1 -p 8001`  │
│  entrypoint: [migrate-if-db-exists] → supervisord                        │
└──────────────────────────────────────────────────────────────────────────┘
        ▲ one published port                 ▼ bind mount
   http://host:8080                    ./project → /project
                                       (mosaic.yaml, schemas/, data/mosaic.db)
```

Contents of the recipe directory:

- `Dockerfile` — multi-stage bundle build (§1.4), digest pins for the aperture image, the `datahelix-mosaic` version, and the modeler ref at top. Modeler + CORS proxy included by default (§1.8); a `--build-arg INCLUDE_MODELER=false` slim variant remains available.
- `nginx.conf` — SPA fallbacks for both apps, `no-store` on `config.js`/`index.html` (per Aperture ADR-0034), proxy block for the Mosaic API.
- `entrypoint.sh` — the §1.7 migrate-then-serve logic + writes Aperture's `/config.js` (reusing its `40-aperture-config.sh` pattern) with `VITE_HIPPO_GRAPHQL_URL=/graphql`.
- `supervisord.conf`.
- `docker-compose.yml` — trivial single-service compose so the run command is `docker compose up` with the volume + port declared (still "single container").
- `README.md` — quickstart: `mosaic init`-style project scaffold, first boot, backup story (SQLite: stop container, copy `data/`), upgrade story (bump image tag → gate check → restart), the no-auth warning.
- `Makefile` targets: `init`, `up`, `migrate` (= restart), `backup`, `gate` (runs `certification/scripts/deploy_gate.sh` against the pinned digests).

#### 2.1a Schema iteration with the Modeler in `solo` — workflow analysis

The Modeler is client-side only (§0 fact 2), so "edit schema in Modeler → Mosaic migrates" needs an explicit transport from the user's browser to the server's `/project/schemas/`. The transport differs by deployment mode, and the recipe must document both honestly:

**Mode L — browser and container on the same machine** (a lab workstation): the FSAA loop. Open `/modeler/`, use the file picker to open `./project/schemas/` on the host — the very directory bind-mounted into the container. Save on the canvas → YAML lands on host disk → `make migrate` (≡ container restart) → additive DDL applied → Aperture re-introspects. Zero extra moving parts; this is also exactly the `ide` recipe's loop, so the muscle memory transfers.

**Mode R — remote `solo`** (container on a VM, user's browser elsewhere): FSAA is useless (it opens the *user's* disk, not the server's). The loop is **git-first**:

1. `/project/schemas/` is a git repo (or subdirectory of one) with a remote; `mosaic init` docs gain a "put your project dir under git" step — good practice regardless.
2. The Modeler clones that remote in-browser (isomorphic-git via the bundled `/cors-proxy/`), the user edits on the canvas, commits, and pushes. Auth: a git token pasted at runtime, or the GitHub device-flow if we bake a client ID (§4.5).
3. The `solo` entrypoint gains an optional **pull-on-boot** step: when `SCHEMA_GIT_REMOTE` (+ optional `SCHEMA_GIT_REF`) is set, it fetches/fast-forwards `/project/schemas` from the remote *before* the migrate step. "Restart the container" then means "pull + migrate + serve" — one motion, consistent with restart-on-migrate.
4. Failure honesty: a breaking schema diff still fail-fasts the boot (§1.7); the container logs name the offending diff and point at `mosaic schema safe-deploy`. The old DB and old schema checkout remain untouched (pull into a staging dir, swap only after migrate dry-run passes).

Mode R adds two cheap pieces (the CORS proxy sidecar, ~30 lines of entrypoint git logic) and one convention (schemas under git). No new component features are required.

**Rejected/deferred alternatives:** manual download-from-Modeler / scp-to-server (works today, no infra, but error-prone and no history — documented as escape hatch only); a schema-upload REST endpoint on Mosaic (bypasses git history and duplicates what git does); and the long-term direction — the Modeler growing a `PlatformAPI` backend that reads/writes schemas *through* a server API with migrate-as-a-button. That last one aligns with the platform's config-as-data ethos and the Modeler's clean platform abstraction (`packages/core/src/platform/PlatformContext.ts`), but it is real feature work in two repos and explicitly post-MVP; if the git-first loop chafes in practice, that's the successor to design (and worth its own proposal + upstream issues).

**Multi-author caveat (documented, not solved):** `solo` is single-user; nothing prevents two people pushing conflicting schema changes to the remote. Git surfaces the conflict, but schema *semantic* review (breaking-change policy, `safe-deploy` discipline) is process, not tooling, at this tier — `team` is where that gets machinery.

### 2.2 `deploy/recipes/ide/` — the development environment

**Audience:** you, iterating on a LinkML schema and seed data for a small deployment; also usable for hacking on Mosaic/Aperture themselves.

The inner loop this recipe is built around:

1. Open the Modeler (`http://localhost:8080/modeler/`), use the FSAA picker to open `./project/schemas/` **on the host** (same directory bind-mounted into the `mosaic` service).
2. Edit classes/slots on the canvas, save — the YAML lands on the host disk.
3. `make migrate` (≡ `docker compose restart mosaic`) — entrypoint diffs schema vs DB, applies additive DDL, refuses breaking changes with a pointer to `mosaic schema safe-deploy`.
4. Reload Aperture — introspection picks up the new types; browse/ingest against them immediately.

Services (compose, all bind-mounted from the project dir):

| service | source | notes |
|---|---|---|
| `mosaic` | pinned image by default; `build:` from a source checkout via compose profile `dev-mosaic` | `--graphql`, port 8001 exposed directly too (API tinkering, `/docs`), optional `--reload` in the source profile |
| `aperture` | published image | `VITE_HIPPO_GRAPHQL_URL` pointed at the nginx-proxied same-origin path (or directly at `:8001` — CORS on Mosaic is then required; same-origin preferred) |
| `modeler` + `cors-proxy` | built from pinned `linkml-modeler-app` ref (profile `modeler`, on by default) | CORS proxy enables in-browser git clone/push of the schema repo for the git-first workflow |
| `gateway` | nginx | same routing as `solo`, so the two recipes feel identical in the browser |

Also in scope for `ide`: a seed-data convention (`./project/seed/` + a documented `mosaic ingest` invocation). The `ide` recipe supports **local development only** — browser and containers on the same machine, so the FSAA inner loop always works. Remote dev environments (Codespaces, devcontainers) are deferred entirely (§4.3).

### 2.3 `deploy/recipes/team/` — small multi-user (specified now, built after `solo`/`ide`)

`solo` split into services + Postgres: `postgres:16`, `mosaic` (postgres extra, `MOSAIC_DATABASE_URL`), `aperture`, `gateway` (nginx — explicitly the placeholder Bridge will replace as sole PEP/PDP). Digest-pinned certified pair, deploy-gate pre-flight, backup = `pg_dump`. Structurally this is the certification stack minus the harness, made user-facing. **Caveat to resolve when building it:** `mosaic migrate` is SQLite-only today — `team` migrations go through `mosaic schema safe-deploy`/pg migration paths, and that asymmetry should be surfaced to Mosaic as a feature request (`migrate` parity on Postgres) rather than papered over in the recipe.

### 2.4 Out of scope

Kubernetes/Helm (Tier 3), Cappella/Canon/Bridge recipes (join `platform-full` when they're consumable), remote multi-author schema editing (git-first Modeler flow exists in `ide` but the server-side auto-pull-and-migrate loop is future work).

---

## 3. Prerequisite fixes (each lands in its home repo, before or with Phase 1)

| # | Repo | Fix | Why |
|---|---|---|---|
| 3.1 | mosaic | **Dockerfile user bug**: creates `hippo` user, chowns/runs as nonexistent `datahelix` → image doesn't build/run as written | `solo` wants to base off (or mirror) a working Mosaic image |
| 3.2 | mosaic | Decide the container FS convention (this proposal: workdir `/project`, explicit `--db-path`/`--config`); align EXPOSE/port docs (8000 vs 8001) | Today's image creates `/data/hippo-db` that nothing uses; SQLite would silently land in the container layer and be lost |
| 3.3 | aperture | Verify a **relative** `VITE_HIPPO_GRAPHQL_URL` (`/graphql`) works through `resolveEndpoint`/urql; document it in ADR-0034's orbit | Enables the zero-CORS same-origin pattern in §2.1; expected to work (`web/src/data/endpoint.ts` passes any non-empty string through) |
| 3.4 | linkml-modeler-app | Contribute a **self-contained multi-stage** `Dockerfile.web` (pnpm build stage → nginx) with `VITE_BASE_URL`/`VITE_GIT_CORS_PROXY` as build args | Current `deploy/web/Dockerfile.web` requires a host-built `dist/`; recipes need reproducible builds at a pinned ref, and `/modeler/` needs a baked base path |
| 3.5 | datahelix | Add `deploy/recipes/` + this ladder to `platform/deployment.md` (Tier 2 gains named recipes; fold the divergent embedded compose example into the `team` recipe) | Single source of truth; today the doc's compose and the root compose contradict each other |

---

## 4. Questions — all decided (owner review, 2026-07-14)

| # | Question | Decision |
|---|---|---|
| 4.1 | hippo → mosaic naming in datahelix | ✅ **Recipes adopt Mosaic now.** The repo-wide catch-up (submodule path/URL, CI, certification stack, compose, docs) is tracked in **[#49](https://github.com/BU-Neuromics/datahelix/issues/49)** to pick up later; historical docs keep the Hippo name per the forward-only convention. |
| 4.2 | Modeler in the production `solo` image? | ✅ **Yes, by default** — schema self-service is a first-class capability. Workflow consequences worked through in §2.1a (FSAA loop locally, git-first loop remotely, pull-on-boot entrypoint). |
| 4.4 | Bundled `solo` image: certified ledger artifact, or "built from a certified pair"? | ✅ **Middle path.** Phase 1 ships as "built from certified pair" **plus** a mandatory datahelix CI job running the certification Playwright scenarios (or a subset) against the built `solo` container — designed so that job *is* the future certification run. The `solo` gate check verifies the inner pair digests (recorded as image labels) form a certified pair. Once the recipe stabilizes (end of Phase 3), promote the job into the certification harness and extend the ledger with a `bundle` artifact kind (bundle digest → inner pair digests). Rationale kept for the record: "built from certified pair" alone leaves the bundle's changed topology (same-origin proxying, relative GraphQL URL, supervisord, migrate/pull-on-boot) untested and gives the gate no bundle digest to check; full certification from day one costs ledger/tooling work while the recipe is still churning. |
| 4.3 | Devcontainer wrapping the `ide` recipe? | ✅ **Deferred entirely — not scheduled in any phase.** The `ide` recipe supports **local development only** (sole developers today; Codespaces value unclear, and the FSAA inner loop breaks there since the browser picks files on the user's machine while the project dir lives in the remote codespace). Revisit only if a concrete need appears — cheap to add at any time; nothing in the recipes depends on it. |
| 4.5 | GitHub OAuth client ID for the Modeler's git flows (build-time `VITE_GITHUB_CLIENT_ID`) | ✅ **Leave unset for MVP** (default stood, no objection). Token-paste covers the git-first Mode R flow; the FSAA local loop needs nothing. Revisit when Mode R gets real use. The Modeler holds tokens in memory only — never persisted. |

---

## 5. Execution phases

- **Phase 1 — `solo`**: land 3.1–3.4 fixes; build `deploy/recipes/solo/` with the Modeler + CORS proxy included (§1.8) and the pull-on-boot entrypoint option (§2.1a Mode R); smoke-test: init → up → browse in Aperture → edit schema on host (Mode L loop) → restart → migrated. Add a datahelix CI job that builds the bundle image and runs that smoke loop headlessly (this job is also the §4.4 middle-path seed).
- **Phase 2 — `ide`**: compose + Makefile + Modeler/CORS-proxy profile (shares the 3.4 image); document the four-step inner loop; seed-data convention.
- **Phase 3 — polish & ladder**: `team` recipe; relocate root compose to `platform-full`; promote the `solo` CI job into the certification harness + ledger `bundle` kind (§4.4); update `platform/deployment.md` (3.5); ratify the platform ADR (1.11). (Devcontainer intentionally absent — deferred per §4.3.)

Each phase is independently shippable; Phase 1 alone delivers the production MVP, Phase 2 alone (atop it) delivers the development environment.
