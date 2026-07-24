# Change: Support existing Mosaic projects whose schema requires a custom reference-loader package

## Why

The `solo` recipe (`deploy/recipes/solo/`) is designed to run any Mosaic
project pointed at by `PROJECT_DIR` — this already works for projects whose
layout matches the expected convention (`mosaic.yaml`, `schemas/`,
`data/mosaic.db`). Live testing against a real, populated Mosaic instance
(78,334 Ensembl genes + 4,179 differential-expression results) confirmed that
part works once the project files are renamed into the expected layout.

However, that same schema declares `requires: hippo-reference-ensembl==0.1.0`
— a custom lab Python package (a Mosaic `SchemaPackage`/`ReferenceLoader`)
that contributes the `ensembl:Gene` schema fragment via Python entry-point
discovery. The `solo` bundle image is built only from `datahelix-mosaic` +
Aperture + the LinkML Modeler — it has no mechanism to install a project's
own custom reference-loader packages. Confirmed by live testing: the
container boots, finds the existing database, and then `mosaic migrate`
hard-fails on every restart with:

```
Error during migration: 1 unsatisfied `requires:` pin(s):
  - requires hippo-reference-ensembl but it is not installed. Install with:
    mosaic reference install ensembl --version 0.1.0
    (error_code='HIPPO_REQUIRES_UNSATISFIED', field_name='requires', cycle_path=None)
```

Installing the missing package into a derived image resolved this
completely: `mosaic migrate` proceeded (additive-only, no data loss), and the
full stack — GraphQL introspection, querying, and Aperture — served the real
78,334 genes and 4,179 DE results correctly. So the gap is narrow: the recipe
has no supported way to bring in a project's declared reference-loader
dependency, not a deeper defect in the schema-merge or migrate logic itself.

## What Changes

- Add an **optional, opt-in build-time extension point** to the `solo`
  recipe's `Dockerfile`/`Makefile` for installing extra local Python packages
  (a project's own reference-loader/schema packages) into the bundle image,
  so `mosaic migrate`/`serve` can resolve `requires:` pins the project
  declares.
- Document this in `deploy/recipes/solo/README.md`, alongside the existing
  guidance (carried over from the original documentation-only scope) that
  `PROJECT_DIR` must point at the project root and that an existing project
  needs to match the `mosaic.yaml` / `schemas/` / `data/mosaic.db` naming
  convention.
- Clarify how the ADR-0001 certification gate applies to a bundle built with
  extra packages: `check-pins`/`make gate` still verify the inner Mosaic +
  Aperture digest pair, but a bundle with extra packages layered in is a
  locally-built extension, not the exact certified artifact — this is
  documented as an explicit caveat, matching how the recipe already treats an
  un-certified freshly-bumped frontier as informational.
- Default behavior is unaffected: `make init`'s empty-project workflow,
  existing `PROJECT_DIR` usage without extra packages, and the existing error
  message for genuinely unsupported/incomplete projects all continue to work
  exactly as today.

## Impact

- Affected specs: `solo-recipe` (new capability spec)
- Affected code: `deploy/recipes/solo/Dockerfile`, `Makefile`, `README.md`
  (no changes anticipated to `entrypoint.sh` or `docker-compose.yml` — the
  existing error message is already clear, and `PROJECT_DIR` wiring is
  already correct)
