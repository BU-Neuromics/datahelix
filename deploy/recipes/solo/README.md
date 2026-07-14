# DataHelix `solo` — single-container production MVP

One container, one port: **Aperture** (data explorer) at `/`, the **LinkML
Modeler** (schema editor) at `/modeler/`, and **Mosaic** (`serve --graphql`,
SQLite) proxied same-origin at `/graphql` — with a migrate-on-restart loop for
iterating your schema. Designed in `proposals/deployment-recipes.md` (§2.1).

> **No auth.** Mosaic's bearer guard is a placeholder and this recipe injects
> the token for you; Bridge (the platform's PEP/PDP) is not in this bundle.
> Run it on localhost, behind a VPN/SSH tunnel, or on a trusted network only.

## Quickstart

```bash
cd deploy/recipes/solo
make init     # scaffold ./project (mosaic.yaml, schemas/, data/) from the example
make gate     # certified-frontier pre-flight (platform ADR-0001)
make up       # build the bundle image and start it
```

Then open <http://localhost:8080> (Aperture), <http://localhost:8080/modeler/>
(Modeler), <http://localhost:8080/docs> (API docs). `SOLO_PORT=9090 make up`
to publish elsewhere.

The **project directory** is the whole deployment state: `mosaic.yaml`,
`schemas/*.yaml`, `data/mosaic.db`. Put it under git; back it up with
`make backup`. Point `PROJECT_DIR` at any path to run a different project.

## Iterating your schema

Additive changes (new classes, attributes, enums) are a restart away
(restart-on-migrate, Mosaic v0.1 model). Removals/renames are **not**
auto-applied — plan those with `mosaic schema safe-deploy` first.

**Mode L — browser and container on the same machine.** Open the Modeler,
use *Open* to pick `./project/schemas/` on your disk (the very directory the
container mounts), edit on the canvas, save, then:

```bash
make migrate   # = restart: applies additive DDL, Aperture re-introspects
```

**Mode R — container on a remote host.** The Modeler in your browser cannot
see the server's filesystem; the loop goes through git:

1. Make `project/` (or just its `schemas/`) a git repo with a remote.
2. In the Modeler, clone that remote (the bundle serves a same-origin git
   relay at `/cors-proxy` for exactly this), edit, commit, push.
3. Configure the container with `SCHEMA_GIT_REMOTE=<url>` (optionally
   `SCHEMA_GIT_REF`, and `SCHEMA_GIT_PATH` if the schemas aren't at
   `schemas/` in that repo), then `make migrate`.

On every (re)start with `SCHEMA_GIT_REMOTE` set, the entrypoint fetches the
remote into a staging directory, **dry-runs the migration before touching
anything**, then swaps the schemas in and applies. A failed plan aborts the
boot with the old schemas and database untouched.

Escape hatch: `scp` the YAML into `project/schemas/` and `make migrate`.

## How it fits together

```
:8080 nginx ── /            → Aperture SPA   (from the certified aperture image)
          ├── /modeler/     → LinkML Modeler (static build at a pinned ref)
          ├── /cors-proxy/  → git relay for the Modeler (node, localhost:9999)
          ├── /graphql      → mosaic serve --graphql (localhost:8001)  [+ bearer]
          └── /health /docs /redoc /openapi.json → mosaic serve
supervisord: nginx + mosaic + cors-proxy ─ entrypoint: [pull] → migrate → serve
volume: ./project → /project   (workdir; mosaic.yaml auto-discovered)
```

Same-origin proxying is the certification-proven seam (the certify stack runs
the identical topology): Aperture is runtime-configured with the **relative**
endpoint `/graphql`, so there is no CORS anywhere. Override any Aperture
runtime var (`VITE_HIPPO_GRAPHQL_URL`, `VITE_HIPPO_CONTROL_PLANE_URL`,
`VITE_WORKFLOWS`, `VITE_NAV`) via compose environment (ADR-0034).

## Certification (platform ADR-0001)

The bundle is **built from the certified pair**: the Dockerfile pins the
hippo and aperture images by digest, and `make check-pins` fails if they
drift from `certification/composition.lock.json` (this is the recipe's own
invariant, enforced in CI). The pins are recorded as OCI labels
(`org.datahelix.solo.*`) on the bundle image for provenance.

`make gate` is the **deploy-time pre-flight**: it runs `check-pins` and then
the ADR-0001 ledger gate (`deploy_gate.sh`), which refuses to proceed unless
the pinned pair has a passing ledger entry. Run it before deploying to a real
environment. Note the gate depends on ledger state maintained by the certify
workflow — a freshly-bumped frontier may need an on-demand certification run
before it passes; that is expected and separate from whether the recipe
builds. (The recipe smoke CI therefore treats the gate as informational.)
Promoting the bundle itself to a certified ledger artifact is the Phase-3
follow-on (proposal §4.4).

## Upgrading

1. The certification frontier advances (new certified pair in the lock).
2. Update the Dockerfile's `HIPPO_IMAGE` / `APERTURE_IMAGE` ARGs to match
   (`make check-pins` confirms), bump `MODELER_REF` if desired.
3. `make gate && make up` — the image rebuilds, migrate-on-boot handles
   additive schema evolution, SQLite data carries over in `project/`.

## Limitations (deliberate, MVP)

- **Single-user, no auth** (see banner above). Multi-user lands with Bridge
  and the `team` recipe.
- Only `/graphql`, `/health`, `/docs`, `/redoc`, `/openapi.json` are proxied;
  Mosaic's full REST surface needs the optional `8001` port mapping
  (commented in `docker-compose.yml`).
- Container processes run as root (bind-mount ownership simplicity); harden
  in `team`.
- Migrations are additive-only; breaking changes are a manual
  `schema safe-deploy` operation.
- The certified frontier currently pins a pre-rename (`hippo`) component
  image; the entrypoint abstracts the CLI name, and data-contract
  identifiers keep the `hippo` spelling by design (Mosaic ADR-0004).
