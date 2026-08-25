# ADR-0005: Drop the LinkML Modeler from the deployment recipes

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** labadorf, design session
- **Supersedes:** [`proposals/deployment-recipes.md`](../../../proposals/deployment-recipes.md) decision **1.8** (owner decision of 2026-07-14, "Modeler ships in `solo` by default"), and the Modeler/`cors-proxy` portions of decision 1.9 and §2.2 carried into [ADR-0004](./ADR-0004-ide-recipe-live-development-loop.md)
- **Related:** [ADR-0004](./ADR-0004-ide-recipe-live-development-loop.md) (the `ide` recipe; its gateway routing loses `/modeler/` and `/cors-proxy/`); [BU-Neuromics/linkml-modeler-app#172](https://github.com/BU-Neuromics/linkml-modeler-app/issues/172) (the EOL-Node blocker); datahelix #84 (the `ide` Modeler task this closes as superseded), #72 / #85 (the EOL Node pin this finishes)

## Context

Decision 1.8 made the LinkML Modeler a first-class part of `solo` on the
reasoning that "users iterating their own schema is a first-class platform
capability, not a dev-only feature." That was a defensible call at the time.
Six weeks of building on it have changed the facts.

**It is not wired into anything.** The Modeler is served as a static SPA at
`/modeler/` and shares no state with the rest of the bundle. It cannot read the
server's schema directory at all — it is a purely client-side app using the
browser's File System Access API (`deployment-recipes.md` §0 fact 2). Every
loop that closes between it and Mosaic closes through something else: the host
filesystem (Mode L) or a git remote (Mode R). Nothing in Aperture, Mosaic, or
the certification harness references it.

**It is the most expensive thing in the bundle by a wide margin.** It is the
only component built from source in a production recipe — an external repo
(`BU-Neuromics/linkml-modeler-app`) cloned at a pinned commit and built with
corepack pnpm — which is a direct exception to decision 1.4's "never build
components from source in a production recipe". It also drags in a `cors-proxy`
sidecar, a Node runtime binary copied into the final image, `libstdc++6` to run
that binary, a supervisord program, and two nginx location blocks.

**It is the last thing holding the platform on an EOL runtime.** Node 20 went
EOL 2026-04-30. #85 moved the `node-runtime` stage to Node 26, but the
`modeler-build` stage is still `node:20-alpine` and cannot move until the
upstream repo does — its own CI and `engines` floor are still Node 20
(linkml-modeler-app#172, filed 2026-08-21, untriaged). So a component that is
not wired into anything is pinning a production image to an end-of-life
toolchain, and the fix is gated on a repo outside this one.

**It is not needed for the DataHelix MVP.** Schema authoring by hand plus
`make migrate` is the loop the recipes actually document and test.

**The question:** does the Modeler stay in the recipe family, or come out?

## Decision

**The LinkML Modeler will not ship in any DataHelix deployment recipe.**

- `solo` drops the `modeler-build` stage, the `cors-proxy` sidecar, the Node
  runtime binary and its `libstdc++6` dependency, the supervisord program, and
  the `/modeler/` and `/cors-proxy/` nginx locations.
- `ide` does not gain them — datahelix #84 closes as superseded rather than
  being implemented.
- `demo` is unaffected; it never had them.
- **Mode R stays.** The `SCHEMA_GIT_REMOTE` pull-on-boot path was introduced so
  the Modeler could reach a remote deployment's schemas, but it is useful for
  any editing workflow — edit in whatever tool, push, restart. Only the
  `cors-proxy` (which exists solely for the Modeler's in-browser
  isomorphic-git) goes. Mode L likewise stays: it is just "edit the
  bind-mounted `schemas/` directory", which needs no server-side support.

Schema authoring is by hand, or in the Modeler run separately by the user
against their own checkout. The recipes keep `make migrate` as the seam.

This is a reversal, not a refinement: decision 1.8 is superseded, not amended.

## Consequences

**What becomes true**

- **No Node anywhere in `solo`.** Both Node pins disappear rather than moving,
  which completes the platform's Node 26 migration by elimination — every
  remaining Node in the repo (Aperture's image and CI, the certification
  Playwright harness, `ide`'s Vite service) is already on 26.
- `solo`'s image gets materially smaller and faster to build, and stops
  depending on an external repo's build system, its pnpm version, and a pinned
  commit that nobody was bumping.
- Decision 1.4's "never build components from source in a production recipe"
  becomes true without exception.
- The `solo` recipe's surface shrinks to what is actually tested: Aperture,
  Mosaic, the same-origin seam, and the migrate loop.

**What becomes harder**

- **Schema authoring loses its GUI in the bundle.** A user who wants the canvas
  now runs the Modeler themselves against their `schemas/` directory. For Mode
  L that is genuinely equivalent — the Modeler always read the *host*
  filesystem, never the container's, so running it separately changes nothing
  about how it reaches the files. For Mode R it is a real loss: the bundled
  `cors-proxy` was what let the browser clone and push the schema repo
  same-origin. Users on that path need a CORS-enabled git host or their own
  proxy.
- Anyone currently relying on `/modeler/` in a deployed `solo` loses it on
  upgrade. The route returns an explicit **410 Gone** with a pointer, rather
  than falling through to the SPA handler — which would otherwise serve
  Aperture's shell and read as "the Modeler failed to load" instead of "the
  Modeler is gone". This is an MVP-stage recipe with no compatibility
  guarantee, but it is called out in the recipe's upgrade notes.

**Reversibility**

Low cost to undo. If the Modeler becomes wired into the platform — most
plausibly via the `PlatformAPI` backend sketched in §2.1a's rejected
alternatives, which would let it read and write schemas *through* a server API
instead of the browser filesystem — that is a different and better integration
than serving its static bundle next door, and would warrant its own ADR rather
than reinstating this one.

## Alternatives considered

**Keep it and wait for the upstream Node bump.** Rejected: it makes a
production image's toolchain currency depend on an unrelated repo's
maintenance cadence, for a component that is not wired into anything.
linkml-modeler-app#172 has been open since 2026-08-21 with no triage, and there
is no reason to think the recipes should block on it.

**Keep it but pin a prebuilt Modeler image.** Rejected: no such image is
published, so this is really "publish and maintain a Modeler image" — real work
in another repo to keep shipping something the MVP does not need.

**Keep it in `solo`, skip it in `ide`.** Rejected as the worst of both: it
retains every cost (EOL Node, source build, sidecar, exception to 1.4) in the
recipe where the stakes are highest — the one people actually deploy — while
denying it to the recipe where a schema-editing GUI would plausibly be most
useful.

**Remove Mode R along with the `cors-proxy`.** Rejected: git-based schema
delivery is orthogonal to how the YAML was authored. Pull-on-boot with a
migrate dry-run before the swap is a good property for any remote deployment
and costs nothing to keep.
