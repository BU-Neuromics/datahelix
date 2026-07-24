## Context

The `solo` recipe's certified-frontier model (ADR-0001) builds the bundle
image `FROM` digest-pinned `datahelix-mosaic`/Aperture images — deliberately
never building components from source, so the bundle stays traceable to a
certified pair. That model didn't anticipate a project schema declaring a
`requires:` pin on a package outside that certified pair. Live testing (see
proposal) confirmed this is a hard boot-time failure, not a cosmetic one:
`mosaic migrate` refuses to run at all until the pin resolves, even though
the referenced data already exists in the database and needs no
re-provisioning.

## Goals / Non-Goals

- Goals:
  - Let a `solo` deployment install a project's own declared reference-loader
    package(s) so `mosaic migrate`/`serve` can resolve `requires:` pins
    against an already-populated database.
  - Keep this fully opt-in — zero effect on the default `make init` /
    empty-project path or existing `PROJECT_DIR` users who don't need it.
  - Keep the mechanism simple: a project supplies its own package source
    locally (build-time), not a runtime fetch from an arbitrary remote.
- Non-Goals:
  - Re-running data provisioning (`mosaic reference install ...`) — the
    target scenario is an *already-populated* database; provisioning-on-boot
    is out of scope.
  - Making the custom-package bundle itself a certified ledger artifact —
    it's explicitly an uncertified, locally-built extension.
  - General plugin marketplace / remote package discovery — one project, one
    local build, matching the recipe's existing "your project directory is
    the whole deployment state" philosophy.

## Decisions

- **Decision: build-arg pointing at a local directory of packages, not a
  runtime pip install.** A `Dockerfile` `ARG EXTRA_PACKAGES_DIR` (empty by
  default) that, if the referenced directory has content at build time,
  `pip install`s every package found there. Runtime pip install was rejected:
  it re-runs on every restart (slow, and a foot-gun for a "no-auth, trusted
  network only" recipe pulling arbitrary code at boot), and conflicts with
  the recipe's existing build-time-only philosophy (§1.4 of
  `proposals/deployment-recipes.md`: "never build components from source in
  a production recipe" — installing a project's *own* declared dependency at
  build time is consistent with that principle; doing it at every container
  start is not).
  - Alternatives considered: a `requirements.txt` fetched from
    `SCHEMA_GIT_REMOTE` alongside schemas (rejected — conflates two different
    trust boundaries, code vs. schema data, and the git-sync path is
    explicitly schema-only per the existing Mode R design); a runtime
    `pip install` in `entrypoint.sh` before migrate (rejected, above).
- **Decision: certification gate stays scoped to the inner pair.**
  `check-pins`/`make gate` don't change — they still verify the Mosaic +
  Aperture digest pair is a certified pair. A bundle built with
  `EXTRA_PACKAGES_DIR` set is documented as **not** the exact certified
  bundle artifact; this mirrors the existing informational-gate treatment for
  a freshly-bumped, not-yet-certified frontier (README §Certification).
  Rationale: solving "should a custom-package bundle be certifiable" is a
  separate, larger question (ledger `bundle` artifact kind, already flagged
  as future work in `proposals/deployment-recipes.md` §4.4) — out of scope
  for unblocking this narrow, already-tested case.
- **Decision: no `entrypoint.sh` change.** The existing
  `HIPPO_REQUIRES_UNSATISFIED` error message is already specific and
  actionable (names the missing package and the version). Only the README
  gains a section pointing at `EXTRA_PACKAGES_DIR` as the fix when this error
  is seen.

## Risks / Trade-offs

- **Supply chain**: installing arbitrary local packages into a production
  image, even opt-in, widens what runs inside the container. Mitigation:
  packages must come from a directory the user explicitly points at (their
  own project directory or a path they control) — never fetched from a
  remote URL at build or run time; the recipe's existing no-auth /
  trusted-network posture already assumes a trusted operator.
- **Certification drift**: a custom-package bundle is, by design, outside the
  certified-pair guarantee. Documented explicitly rather than silently
  glossed over, so `make gate` output/docs make clear this variant is
  informational-only, consistent with existing precedent in the README.

## Migration Plan

No migration — purely additive (`ARG` defaults to unset/no-op; existing
Dockerfile stages, `docker-compose.yml`, and `entrypoint.sh` behavior
unchanged for every existing user).

## Open Questions

- Should `EXTRA_PACKAGES_DIR` support a `requirements.txt`-style pinned list
  in addition to raw local package directories? Deferred to implementation —
  start with the minimal local-directory case proven in testing (a plain
  `pip install <path>` succeeded with `--no-deps` against the one package
  tested); revisit if a real project needs pinned transitive dependencies.
