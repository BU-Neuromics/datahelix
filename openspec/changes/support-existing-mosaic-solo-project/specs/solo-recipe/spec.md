## ADDED Requirements

### Requirement: Load an existing Mosaic project via PROJECT_DIR
The `solo` recipe SHALL run against any existing Mosaic project directory
supplied via `PROJECT_DIR`, provided that directory contains `mosaic.yaml` at
its root, a `schemas/` directory of LinkML schema file(s), and
`data/mosaic.db`.

#### Scenario: Existing populated database is preserved and served
- **WHEN** `PROJECT_DIR` points at a project whose `data/mosaic.db` already
  contains records
- **THEN** the entrypoint detects the existing database, runs
  `mosaic migrate` (additive-only) instead of first-boot initialization, and
  the existing records remain queryable via GraphQL and visible in Aperture

#### Scenario: Default empty-project workflow is unaffected
- **WHEN** no `PROJECT_DIR` is supplied (or `make init` scaffolds a fresh
  `./project`)
- **THEN** the recipe behaves exactly as before this change: a new, empty
  Mosaic instance is initialized on first boot

### Requirement: Support a project's custom reference-loader package dependency
The `solo` recipe SHALL provide an opt-in, build-time mechanism
(`EXTRA_PACKAGES_DIR`) for installing a project's own declared Python
reference-loader/schema package(s) into the bundle image, so that
`mosaic migrate`/`serve` can resolve `requires:` pins the project's schema
declares.

#### Scenario: Schema requires an uninstalled reference-loader package
- **WHEN** a project's schema declares `requires: <package>==<version>` and
  that package is not installed in the bundle image
- **THEN** `mosaic migrate` fails fast with a clear, actionable error naming
  the missing package and version, and the container does not silently start
  serving with a partially-resolved schema

#### Scenario: EXTRA_PACKAGES_DIR resolves the missing dependency
- **WHEN** `EXTRA_PACKAGES_DIR` is set at build time to a local directory
  containing the project's required reference-loader package
- **THEN** the package is installed into the bundle image at build time,
  `mosaic migrate` succeeds against the existing database (additive-only, no
  data loss), and the resolved data is servable via GraphQL and Aperture

#### Scenario: Default build is unaffected when EXTRA_PACKAGES_DIR is unset
- **WHEN** `EXTRA_PACKAGES_DIR` is not set (the default)
- **THEN** the bundle image build is identical to today's build — no new
  layers, packages, or behavior are introduced

### Requirement: Certification gate scope is unchanged by the extension point
The ADR-0001 certification gate (`check-pins`, `make gate`) SHALL continue to
validate only the inner Mosaic + Aperture digest pair, regardless of whether
`EXTRA_PACKAGES_DIR` was used to build the image.

#### Scenario: Gate treats a custom-package bundle as informational
- **WHEN** a bundle is built with `EXTRA_PACKAGES_DIR` set
- **THEN** `make gate` still checks the inner certified pair as usual, and
  the documentation makes explicit that such a bundle is a locally-built
  extension rather than the exact certified artifact
