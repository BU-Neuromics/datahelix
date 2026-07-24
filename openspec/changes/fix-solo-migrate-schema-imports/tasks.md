## 1. Fix

- [x] 1.1 Change `deploy/recipes/solo/entrypoint.sh`'s migrate invocation to
      run with cwd set to `$PROJECT/schemas` (via a subshell), so relative
      sibling `imports:` resolve correctly for multi-file schemas.
- [x] 1.2 Verify no regression against a single-file schema with only
      package-level imports (`hippo-example`) — confirmed: boots healthy,
      serves 78,334 real rows.
- [x] 1.3 Verify the fix against a real multi-file schema with local
      sibling imports (`hippo-benchmark` / `brainbank.yaml`) — confirmed:
      boots healthy, GraphQL + Aperture serve real donor/assay records.

## 2. Documentation

- [ ] 2.1 Add a note to `deploy/recipes/solo/README.md`: if your schema
      splits across files with local `imports:`, set `mosaic.yaml`'s
      `schema_path` to the tree-root file (e.g. `schemas/brainbank.yaml`),
      not just the `schemas/` directory — required for `mosaic serve` to
      resolve the same imports (migrate is unaffected by this setting; it
      always scans the whole `schemas/` directory).

## 3. Regression coverage

- [ ] 3.1 Add a smoke-test case: a project whose schema splits across
      multiple files with local `imports:` (mirroring the pattern above);
      assert migrate succeeds and the container serves real rows.
