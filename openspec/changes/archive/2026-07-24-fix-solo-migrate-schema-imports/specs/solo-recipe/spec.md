## ADDED Requirements

### Requirement: Migrate resolves multi-file schemas with local cross-file imports
The `solo` recipe's entrypoint SHALL run `mosaic migrate` such that a
schema's relative sibling `imports:` (LinkML files in the same `schemas/`
directory importing one another) resolve correctly, regardless of the
container's working directory.

#### Scenario: Multi-file schema with local imports migrates successfully
- **WHEN** a project's `schemas/` directory contains a tree-root file that
  imports sibling files in the same directory (e.g. `imports: - core`)
- **THEN** `mosaic migrate` resolves those imports without error and applies
  the migration against the existing database

#### Scenario: Single-file schema is unaffected
- **WHEN** a project's schema is a single file with only package-level
  imports (no local sibling files)
- **THEN** `mosaic migrate` continues to succeed exactly as before this
  change
