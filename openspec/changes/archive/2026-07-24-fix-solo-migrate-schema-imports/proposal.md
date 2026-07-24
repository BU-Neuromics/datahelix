# Change: Fix solo recipe migration for schemas with local cross-file imports

## Why

Live-tested the `solo` recipe against a real, populated Mosaic project
(`hippo-benchmark`, a vendored copy of `brainbank-hippo-schema` — 90 tables,
real donor/assay records) via `PROJECT_DIR`. The schema's tree-root file
(`brainbank.yaml`) uses a completely standard LinkML pattern: `imports:` on
sibling files in the same directory (`core`, `anatomy`, `person`, `tissue`,
`dataset`, `analysis`, `pathology`).

The container crash-looped on every restart with:
```
Error during migration: [Errno 2] No such file or directory: '/project/pathology.yaml'
```

Root cause, confirmed by direct testing inside the bundle image: `mosaic
migrate --schema-dir <dir>` resolves a schema's relative sibling `imports:`
**relative to the process's current working directory**, not relative to
the `--schema-dir` path itself. `entrypoint.sh` always invokes migrate from
`/project` (the container `WORKDIR`) while passing
`--schema-dir "$PROJECT/schemas"` — a directory one level below cwd — so any
schema with local cross-file imports fails to resolve, regardless of what
`mosaic.yaml` itself says.

This is a different, narrower bug than the `requires:`
reference-loader-package gap already captured in
`support-existing-mosaic-solo-project`: that one is about an external
Python package dependency; this one is about the migrate CLI's own path
resolution, and blocks a plain, self-contained, no-external-dependency
schema — likely the more common case.

Confirmed fix: running migrate with cwd set to the schema directory itself
(`(cd "$PROJECT/schemas" && mosaic migrate --schema-dir . --db-path "$DB")`)
resolves correctly. `mosaic serve` was not affected by the same bug — it
already resolves cross-file imports correctly when `mosaic.yaml`'s
`schema_path` points at the tree-root **file** (e.g.
`schemas/brainbank.yaml`), which is the pattern the recipe's own
`example-project/mosaic.yaml` comment already documents. Full end-to-end
verification (GraphQL query + Aperture UI) confirmed real donor and assay
records serve correctly once both pieces are in place.

## What Changes

- Fix `deploy/recipes/solo/entrypoint.sh`'s migrate invocation to resolve
  relative imports correctly for schemas with local cross-file imports (run
  migrate with cwd = the schema directory).
- Document in `deploy/recipes/solo/README.md` that a project whose schema
  splits across files with local `imports:` must set `mosaic.yaml`'s
  `schema_path` to the tree-root file (not just the `schemas/` directory) —
  already true for `serve`, now also required knowledge for users debugging
  a migrate failure.
- No change to `docker-compose.yml`, `Makefile`, or the `PROJECT_DIR`
  contract — this is a pure entrypoint bug fix.

## Impact

- Affected specs: `solo-recipe`
- Affected code: `deploy/recipes/solo/entrypoint.sh`,
  `deploy/recipes/solo/README.md`
- Regression risk: low — the fix only changes the working directory for one
  subprocess invocation inside a subshell; the outer entrypoint's cwd and
  all other steps are unaffected. Verified against both a schema without
  cross-file imports (`hippo-example`, single schema file) and one with
  (`hippo-benchmark`, 8 files) to confirm no regression for the simple case.
