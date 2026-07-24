## 1. Recipe: extension point for custom reference-loader packages

- [ ] 1.1 Add `ARG EXTRA_PACKAGES_DIR` (default empty) to
      `deploy/recipes/solo/Dockerfile`; if the directory has content at build
      time, `pip install` every package found there into the mosaic stage.
      No-op when unset/empty — default build is byte-for-byte unaffected.
- [ ] 1.2 Add a `Makefile` passthrough (e.g. `EXTRA_PACKAGES_DIR` build-arg on
      `make up`/`make gate`) so it's usable without hand-editing
      `docker-compose.yml`.
- [ ] 1.3 Verify `check-pins`/`make gate` still only validate the inner
      Mosaic + Aperture digest pair and are unaffected by the extension
      point.

## 2. Documentation

- [ ] 2.1 Add a "Loading an existing Mosaic project" section to
      `deploy/recipes/solo/README.md`: `PROJECT_DIR` must point at the
      project root (not `schemas/`), and the project must match the
      `mosaic.yaml` / `schemas/*.yaml` / `data/mosaic.db` naming convention
      (renames only — no recipe change needed for this part, confirmed by
      live testing).
- [ ] 2.2 Add a "Custom reference-loader packages" subsection documenting
      `EXTRA_PACKAGES_DIR`: when you'd need it (the
      `HIPPO_REQUIRES_UNSATISFIED` error), how to set it, and the explicit
      caveat that a bundle built this way is not the certified artifact
      `make gate` expects — informational only for that variant.
- [ ] 2.3 Note that the migrate step always uses `$PROJECT/schemas` and
      ignores `mosaic.yaml`'s own `schema_path` field — non-obvious from the
      README today.

## 3. Regression coverage

- [ ] 3.1 Add a smoke-test case: scaffold a small project whose schema
      declares a trivial `requires:` on a local test package; assert the
      default build's `mosaic migrate` fails with the expected
      `HIPPO_REQUIRES_UNSATISFIED` error, and that setting
      `EXTRA_PACKAGES_DIR` resolves it and the container serves the
      existing data.
- [ ] 3.2 Add/confirm a smoke-test case that the default `make init` +
      empty-project flow is completely unaffected by 1.1–1.2.
