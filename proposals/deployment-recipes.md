# DataHelix deployment recipes — MVP single-container, IDE, and the scale ladder

**Status:** 🟡 **Draft — for discussion.** Nothing here is locked; §1 decisions are proposals with recommended defaults. Written 2026-07-14 from a verified survey of the four repos (datahelix, mosaic, aperture, linkml-modeler-app).
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
| 1.3 | `solo` shape | **One container, one published port.** nginx front: Aperture SPA at `/`, Modeler at `/modeler/` (optional), reverse-proxy `/graphql` + REST + `/docs` to uvicorn on localhost. `mosaic serve --graphql` on SQLite. | Same-origin proxying sidesteps CORS entirely and means `VITE_HIPPO_GRAPHQL_URL=/graphql` (relative URL — verify once, expected to work since urql accepts relative URLs; fallback is absolute URL injection at start, which ADR-0034 already supports). |
| 1.4 | `solo` image composition | **Build `FROM` the published, digest-pinned component images** — python base with `datahelix-mosaic[graphql]` installed (or `FROM` the fixed Mosaic image) + `COPY --from=ghcr.io/bu-neuromics/aperture@sha256:… /usr/share/nginx/html /srv/aperture` + Modeler dist from a pinned build. | Keeps the bundle honest to ADR-0001: the pair inside the bundle is a ledger-certified pair; the bundle Dockerfile is where the digests are pinned. Never build components from source in a production recipe. |
| 1.5 | `solo` process supervision | **supervisord** (or s6-overlay) running nginx + `mosaic serve`; entrypoint runs the migrate step first (§2.1) | Two processes in one container is a deliberate, documented MVP trade-off; `team` splits them. |
| 1.6 | Storage & state | **One host "project directory" bind-mounted at `/project`**: `mosaic.yaml`, `schemas/`, `data/mosaic.db`. Container workdir = `/project`. | Matches `mosaic init` output 1:1, makes the deployment a git-versionable folder, and is exactly the directory the Modeler edits via FSAA in the IDE flow. Explicit `--db-path /project/data/mosaic.db` — never rely on cwd-relative defaults inside a container. |
| 1.7 | Migrate-on-start policy | Entrypoint: if `data/mosaic.db` exists → `mosaic migrate --schema-dir schemas --db-path data/mosaic.db` (fail-fast on breaking changes, i.e. no `--allow-breaking`); if absent → skip (first boot self-initializes). Then `exec` serve. | Encodes the restart-on-migrate model: "restart the container" = "apply additive schema changes." Breaking changes intentionally stop the boot and point at `mosaic schema safe-deploy`. |
| 1.8 | Modeler inclusion | **Optional in `solo` (build-arg / image variant), on by default in `ide`.** No CORS proxy in `solo`; CORS proxy enabled in `ide` (compose profile) for remote-git workflows. | In a remote `solo` deployment the Modeler can't reach the server's schema dir anyway (§0 fact 2), so it's only decorative there unless the user works git-first. In `ide` on localhost it's the centerpiece. |
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
│   ├── /modeler/    → LinkML Modeler SPA (static, optional variant)       │
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

- `Dockerfile` — multi-stage bundle build (§1.4), digest pins for the aperture image and the `datahelix-mosaic` version at top, `ARG INCLUDE_MODELER=false`.
- `nginx.conf` — SPA fallbacks for both apps, `no-store` on `config.js`/`index.html` (per Aperture ADR-0034), proxy block for the Mosaic API.
- `entrypoint.sh` — the §1.7 migrate-then-serve logic + writes Aperture's `/config.js` (reusing its `40-aperture-config.sh` pattern) with `VITE_HIPPO_GRAPHQL_URL=/graphql`.
- `supervisord.conf`.
- `docker-compose.yml` — trivial single-service compose so the run command is `docker compose up` with the volume + port declared (still "single container").
- `README.md` — quickstart: `mosaic init`-style project scaffold, first boot, backup story (SQLite: stop container, copy `data/`), upgrade story (bump image tag → gate check → restart), the no-auth warning.
- `Makefile` targets: `init`, `up`, `migrate` (= restart), `backup`, `gate` (runs `certification/scripts/deploy_gate.sh` against the pinned digests).

**Schema iteration in `solo`:** supported but blunt — edit `./project/schemas/*.yaml` on the host by any means, `docker compose restart`. Aperture re-introspects on reload and the UI follows the schema. That is the whole "incorporated `mosaic migrate` process."

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

Also in scope for `ide`: a seed-data convention (`./project/seed/` + a documented `mosaic ingest` invocation), and — as a stretch — a devcontainer that wraps this compose for one-click use from VS Code (open question 4.3).

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

## 4. Open questions (blocking discussion, not blocking Phase 1 prep)

| # | Question | Default if no objection |
|---|---|---|
| 4.1 | **hippo → mosaic naming in datahelix**: submodule still points at `BU-Neuromics/hippo`; certification stack, compose, CI all say `hippo`. Do recipes adopt `mosaic` naming now (matching the standalone repo/PyPI name) while the rest of the repo catches up, or stay `hippo`-consistent? | Recipes say **Mosaic** (they're new, user-facing, and the rename is decided per Mosaic ADR-0004); the submodule bump / repo-wide rename is its own proposal |
| 4.2 | Is the Modeler in the **production** `solo` image at all, given it can't see server schemas remotely? | Ship as opt-in build variant, default off (per §1.8) |
| 4.3 | Devcontainer wrapping the `ide` recipe? | Stretch goal, Phase 3 |
| 4.4 | Should the bundled `solo` image itself become a certified artifact in the ledger (new artifact kind), or is "built from a certified pair" enough? | "Built from certified pair" for MVP; ledger extension deferred |
| 4.5 | GitHub OAuth client ID for the Modeler's git-first flow in `ide` (build-time var) — bake a BU-Neuromics OAuth app ID or leave sign-in hidden? | Leave unset/hidden for MVP; FSAA local flow doesn't need it |

---

## 5. Execution phases

- **Phase 1 — `solo`**: land 3.1–3.3 fixes; build `deploy/recipes/solo/` (no Modeler variant yet); smoke-test: init → up → browse in Aperture → edit schema on host → restart → migrated. Add a datahelix CI job that builds the bundle image and runs that smoke loop headlessly.
- **Phase 2 — `ide`**: compose + Makefile + Modeler/CORS-proxy profile (needs 3.4); document the four-step inner loop; seed-data convention.
- **Phase 3 — polish & ladder**: `team` recipe; relocate root compose to `platform-full`; devcontainer (4.3); update `platform/deployment.md` (3.5); ratify the platform ADR (1.11).

Each phase is independently shippable; Phase 1 alone delivers the production MVP, Phase 2 alone (atop it) delivers the development environment.
