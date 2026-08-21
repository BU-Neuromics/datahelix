# DataHelix `ide` — the development environment

Aperture and Mosaic, either or both running **live from your source checkout**,
behind one nginx gateway on one port. Designed in
[`proposals/deployment-recipes.md`](../../../proposals/deployment-recipes.md)
§2.2 / decision 1.9, amended by
[platform ADR-0004](../../../platform/design/decisions/ADR-0004-ide-recipe-live-development-loop.md).

> **Not a deployment.** `ide` is exempt from the ADR-0001 deploy gate because it
> builds from source; nothing it produces is a certified artifact. No auth, no
> gate, no pins to honour. Never point it at real data — use `solo` for that.

## Quickstart

```bash
cd deploy/recipes/ide
make dev      # both components live from source
open http://localhost:8080
```

The first `make dev` installs Aperture's dependencies into a named volume
(30–60s, `make logs-web` to watch). Every start after that is immediate.

## The four ways to run it

| Command | Aperture | Mosaic | Use when |
|---|---|---|---|
| `make up` | pinned image | pinned image | you want a known-good baseline to compare against |
| `make dev` | **source, HMR** | **source** (`make reload-api`) | changing either side, or both |
| `make dev-web` | **source, HMR** | pinned image | front-end only — the common case |
| `make dev-api` | published image | **source** (`make reload-api`) | backend only |

All four serve the same URLs, so nothing in the browser changes when you switch:

```
:8080  /            → Aperture
       /graphql     → Mosaic GraphQL (bearer token injected by the gateway)
       /health      → liveness
       /docs /redoc /openapi.json → FastAPI docs
```

`make down` stops everything. `make clean` also drops the `node_modules`
volume, forcing a clean reinstall.

## The three inner loops

**Front-end.** Edit anything under `aperture/web/src/` and the browser updates
without a reload — Vite HMR, sub-second. No build, no restart, no bind-mounted
`dist/`.

**Mosaic.** Edit anything under `mosaic/src/`, then:

```bash
make reload-api   # ~1s container restart; no rebuild
```

This works because the container runs the pinned Mosaic *image* — so every
runtime dependency is already installed — with your checkout mounted at `/src`
and `PYTHONPATH=/src` shadowing the installed package. Verified: `import mosaic`
resolves to `/src/mosaic/__init__.py`, not the image's `site-packages`.

> **Why not `--reload`?** The flag exists on `mosaic serve` but is unusable as
> shipped: `serve` builds the app *object* and passes it to
> `uvicorn.run(app, reload=True)`, and uvicorn requires an **import string** for
> reload — it logs `You must pass the application as an import string` and calls
> `sys.exit(1)`. The container then restart-loops. Reported upstream; when Mosaic
> passes a factory import string, `--reload` goes back into
> `docker-compose.yml` and this step disappears.

**Schema.** Edit `project/schemas/*.yaml`, then:

```bash
make migrate      # additive DDL + restart the API so it re-reads the schema
```

Additive changes only (new classes, attributes, enums) — Mosaic's v0.1 model is
restart-on-migrate. Removals and renames are not auto-applied; plan those with
`mosaic schema safe-deploy` first. `make migrate` finds whichever mosaic
service is running, so it works in every mode.

To edit schemas on a canvas instead of by hand, run the LinkML Modeler
separately for now — it is not yet part of this recipe (see *Not included*).

## Why the endpoint is relative

Aperture is configured with `VITE_HIPPO_GRAPHQL_URL=/graphql` — a **relative**
path, resolved by the browser against the gateway's origin. That is the same
seam `solo` uses in production, which means:

- No CORS configuration exists anywhere in the stack, in dev or in prod.
- Development is not a topology special case. The arrangement you debug is the
  arrangement you ship.

Overriding it with an absolute URL will reintroduce CORS, which Mosaic
deliberately does not serve.

## Ports

`IDE_PORT` (default 8080) changes the published port, and the Vite dev server
follows it automatically — Vite listens on `IDE_PORT` so its HMR client's port
assumption always matches the public origin, at any port:

```bash
IDE_PORT=9090 make dev
```

## Layout

```
docker-compose.yml                 profiles: {aperture,mosaic}-{image,source}
gateway/default.conf.template      envsubst'd; upstreams swap per profile
example-project/                   scaffold copied to ./project by `make init`
project/                           your deployment state (gitignored)
```

The **project directory** holds `mosaic.yaml`, `schemas/`, and
`data/mosaic.db`. `make init` creates it from the example on first run; point
`PROJECT_DIR` at any path to work on a different project. `MOSAIC_SRC` and
`APERTURE_WEB` override the source checkouts if yours live elsewhere.

## How the profile pairs work

Each component has two mutually exclusive compose profiles — `<component>-image`
and `<component>-source` — and the gateway's upstream is set to match by the
Makefile. Both variants of a component are interchangeable from the gateway's
point of view, so `gateway/default.conf.template` has no per-profile branching.

Two details worth knowing if you edit the gateway config:

- Upstreams resolve at **request** time through Docker's embedded DNS
  (`resolver 127.0.0.11`), not at startup. With a literal hostname in
  `proxy_pass`, nginx resolves once at boot and exits if the name is missing —
  the gateway could then only start with every profile running.
- The `/` block carries websocket upgrade headers and a 7-day read timeout.
  Both are required for HMR and inert for the static-image case. Get them wrong
  and the page still loads perfectly while HMR silently does nothing — which is
  exactly the class of invisible failure ADR-0004 exists to remove.

## Not included

- **LinkML Modeler** — `solo` ships it; here it is deferred to its own task, so
  `/modeler/` is not routed yet.
- **Seed data** — the project scaffold is an empty example schema. Whether
  `ide` should seed from the `demo` recipe's generator or a `project/seed/`
  convention is still open.
- **Deploy gate** — deliberately absent (decision 1.10). There is no
  `make gate` and no `check_pins.py` here by design.
