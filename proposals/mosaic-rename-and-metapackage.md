# Mosaic rename + `datahelix` metapackage — execution plan

**Status:** 🟠 **Ready for implementation** — decisions ratified 2026-07-08 as platform
[ADR-0002](../platform/design/decisions/ADR-0002-datahelix-metapackage-and-extras.md)
(metapackage + extras) and Hippo
[ADR-0004](https://github.com/BU-Neuromics/hippo/blob/claude/hippo-package-rename-gq1cne/design/decisions/ADR-0004-rename-hippo-to-mosaic.md)
(rename Hippo → Mosaic). Tracking issues:
[datahelix#47](https://github.com/BU-Neuromics/datahelix/issues/47) (metapackage),
[hippo#113](https://github.com/BU-Neuromics/hippo/issues/113) (rename).
**Goal:** Execute both ADRs across the three repos (hippo, datahelix, aperture) in
agent-sized work packages, each an independently green, reviewable PR.
**Non-goals:** Import-namespace packages (`datahelix.mosaic` — explicitly deferred in
ADR-0002); renaming the LinkML schema vocabulary or any on-disk identifier (see §4);
publishing to PyPI (no dists are published yet — this plan changes *names*, not release
infrastructure); Bridge (not yet built — its extra is added when it exists).

This document is the **cross-repo coordination plan**. The hippo-repo work packages
(WP-H\*) are specified in full in the hippo repo:
[`design/sec9_handoff_mosaic_rename.md`](https://github.com/BU-Neuromics/hippo/blob/claude/hippo-package-rename-gq1cne/design/sec9_handoff_mosaic_rename.md).
An agent implementing hippo#113 needs only that document; an agent implementing
datahelix#47 needs this one.

---

## 0. Current state (verified 2026-07-08)

- **hippo repo** (`BU-Neuromics/hippo`, v0.10.6): package `src/hippo/` (295 `.py` files
  across src+tests), dist name `hippo`, CLI `hippo`, five entry-point groups declared in
  `pyproject.toml` (`hippo.storage_adapters`, `hippo.write_validators`,
  `hippo.schema_packages`, `hippo.reference_loaders`, `hippo.reference_loader_cli`).
  Group resolution is already centralized (`core/factory.py`,
  `core/validation/validators.py`, `core/loaders/discovery.py`,
  `cli/commands/reference.py`) — discovery.py already unions two groups and dedups.
- **Known-red baseline:** exactly one pre-existing test failure on the branch:
  `tests/cli/test_reference_deprovision.py::TestDeprovisionCli::test_cli_deprovision_not_installed_exits_nonzero`.
  Agents must not chase it and must not let the count grow.
- **datahelix repo:** root `pyproject.toml` is `datahelix-platform-tests` (not published;
  the `datahelix` PyPI name is unregistered — verified 404). Canon
  (`canon`, v0.1.0) registers `[project.entry-points."hippo.reference_loaders"]` and
  imports hippo in 6 source files. Cappella (`cappella`, v0.1.0) depends on `hippo` with
  `[tool.uv.sources] hippo = { path = "../hippo", editable = true }` and imports hippo in
  5 files. `tests/platform/` + `tests/contracts/` import hippo in ~10 files.
  `.github/workflows/tests.yml` installs `-e "./hippo[dev]"` (path-based) and has a
  `contracts-hippo-seam` job. `certify.yml` + `certification/` (ADR-0001 ledger) use
  component key strings `hippo=<ver>@<digest>` and inputs `hippo_version`/`hippo_digest`.
  `mkdocs.yml` nav references `hippo/docs/...` (the submodule mount path).
- **aperture repo:** already `datahelix-aperture`; carries `local = ["hippo"]` extra and
  "(Hippo)" in its description.
- **Branches:** all three repos have `claude/hippo-package-rename-gq1cne` carrying the
  ADRs. Implementation lands on these branches (or stacked branches off them).

---

## 1. Decisions (locked)

Decisions below are plan-level; the *what* and *why* live in the ADRs.

| # | Question | Decision | Notes |
|---|---|---|---|
| 1.1 | Sequencing | **Hippo rename (WP-H) merges first**; datahelix consumes it via one submodule-bump PR (WP-D4) | Consumers stay green at every commit — shims + dual registration make old and new coexist |
| 1.2 | Import layout | **Layout A** — bare imports (`import mosaic`, `import canon`), prefixed dists | Per ADR-0002; PEP 420 namespacing deferred |
| 1.3 | Mosaic version | **0.11.0** (from 0.10.6) | Minor bump: additive from the shim's perspective, but a new dist name |
| 1.4 | Back-compat window | Shims (import, CLI, entry-point groups, config/env fallback) live for **≥ 2 minor releases**, removal via a future ADR | No flag day; deprecation warnings from day one |
| 1.5 | Schema vocabulary & on-disk names | **Unchanged** — `hippo_ext`/`hippo_core` LinkML schema names, annotation keys (`hippo_index_partial`, `hippo_search`), SQL identifiers (`hippo_meta`), DB filenames of existing deployments, provenance content | These are **data contracts**, not packaging surface. ADR-0004: "no data-model impact." Renaming them would be a schema/data migration → separate future ADR if ever |
| 1.6 | Submodule mount path | **Stays `hippo/`** until Phase R (repo rename); mkdocs nav and CI paths unchanged until then | Decouples the code rename from path churn |
| 1.7 | Certification ledger | **Append-only history preserved**: existing `hippo=` entries and `certified/aperture-X+hippo-Y` tags are never rewritten; new entries use `mosaic=`; gate/query code learns the alias `hippo ≡ mosaic` | Consistent with ADR-0001 (ledger is append-only, facts never expire) |
| 1.8 | Metapackage location | New top-level **`metapackage/`** directory in this repo (`metapackage/src/datahelix/`) | Root `pyproject.toml` stays `datahelix-platform-tests` |
| 1.9 | `[all]` extra composition | `canon + cappella + aperture` (Bridge added when it exists) | ADR-0002 open question resolved: no phantom extras |
| 1.10 | Umbrella CLI deps | **stdlib only** (argparse + importlib.metadata) | Metapackage adds zero dependencies of its own |

---

## 2. Work packages

Each WP is one agent-sized PR. `Depends on` is a hard merge-order constraint.

### Phase H — hippo repo (issue hippo#113)

**One PR** on `claude/hippo-package-rename-gq1cne`, commits structured WP-H1 → WP-H6.
Full file-level specification: hippo `design/sec9_handoff_mosaic_rename.md`. Summary:

| WP | Scope |
|---|---|
| H1 | Mechanical rename: `git mv src/hippo src/mosaic`; imports + `HippoClient`→`MosaicClient`; dist → `datahelix-mosaic` 0.11.0; CLI → `mosaic`; **respecting the §1.5 carve-out** |
| H2 | Compat shims: `hippo` meta-path alias package (same module objects — isinstance-safe), `hippo` console-script alias, `HippoClient` alias, all with `DeprecationWarning` |
| H3 | Entry points: canonical `mosaic.*` groups dual-registered with legacy `hippo.*`; the four resolution sites read both groups and dedup (mosaic canonical) |
| H4 | Config/env fallback: `mosaic.yaml` preferred / `hippo.yaml` honored with warning; `MOSAIC_*` env vars preferred / `HIPPO_*` honored with warning |
| H5 | Docs/CI/metadata: README, `docs/` (22 files), CLAUDE.md, workflows, CHANGELOG. `design/` history untouched (forward-only convention) |
| H6 | Verification: new `tests/compat/` suite (shim imports, CLI alias, legacy groups, config/env fallback) + full suite green modulo the §0 known-red baseline |

### Phase D — datahelix repo (issue datahelix#47)

**WP-D1 — `datahelix` metapackage.** *Depends on: nothing (merge anytime; pins bite at D4).*
- Create `metapackage/pyproject.toml`:

  ```toml
  [project]
  name = "datahelix"
  version = "1.0.0a1"
  description = "DataHelix platform metapackage - installs the core; extras add components"
  requires-python = ">=3.11"
  dependencies = ["datahelix-mosaic~=0.11"]

  [project.optional-dependencies]
  canon    = ["datahelix-canon~=0.1"]
  cappella = ["datahelix-cappella~=0.1"]
  aperture = ["datahelix-aperture~=0.1"]
  all      = ["datahelix[canon,cappella,aperture]"]

  [project.scripts]
  datahelix = "datahelix.cli:main"
  ```
- `metapackage/src/datahelix/__init__.py` (version via `importlib.metadata`) and
  `cli.py`: `datahelix info` (table of the five component dists: installed?, version,
  via `importlib.metadata.version`), `datahelix doctor` (attempt `import mosaic` etc.
  for installed components; count entry points per `mosaic.*` group; nonzero exit on
  import failure). **Ranged pins only; stdlib only; no business logic** (ADR-0002).
- For in-repo dev, `[tool.uv.sources]` may pin `datahelix-mosaic = { path = "../hippo",
  editable = true }` etc. — dev convenience only, never published semantics.
- Tests: `metapackage/tests/test_cli.py` — `info` runs and lists mosaic; `doctor` exits
  0 with mosaic importable. Add a `metapackage:` job or fold into `tests.yml`.
- **Acceptance:** `uv run --project metapackage datahelix info` works in-repo; wheel
  builds (`uv build metapackage/`); extras resolve names only (no PyPI publish).

**WP-D2 — Canon dist rename + dual registration.** *Depends on: nothing (safe pre-bump).*
- `canon/pyproject.toml`: `name = "datahelix-canon"` (import stays `canon`).
- Duplicate the entry point: keep `[project.entry-points."hippo.reference_loaders"]`
  **and add** `[project.entry-points."mosaic.reference_loaders"]` with the same
  `canon = "canon.hippo_reference.loader:CanonReferenceLoader"` line. Dual-registering
  on the provider side is compatible with both old hippo and new mosaic (unknown groups
  are inert).
- Do **not** touch canon's `import hippo` lines here — they migrate in WP-D4 with the
  submodule bump (the shim keeps them working meanwhile).
- **Acceptance:** canon suite green against the *current* pinned submodule.

**WP-D3 — Cappella dist rename + dependency retarget.** *Depends on: WP-D4 (same PR is
simplest — the dep name `datahelix-mosaic` only resolves against the bumped submodule).*
- `cappella/pyproject.toml`: `name = "datahelix-cappella"`; test extra `"hippo"` →
  `"datahelix-mosaic"`; `[tool.uv.sources]` key `hippo` → `datahelix-mosaic` (path
  `../hippo` unchanged per decision 1.6).

**WP-D4 — Submodule bump + consumer migration (single PR, tree never half-state).**
*Depends on: Phase H merged to hippo `main`.*
- `git submodule update --remote hippo` → pin the rename commit; verify
  `grep '^name' hippo/pyproject.toml` → `datahelix-mosaic`.
- Migrate imports `hippo` → `mosaic` and `HippoClient` → `MosaicClient` in: canon
  (6 files: `cli/commands/status.py`, `resolver/entity_ref.py`, `resolver/planner.py`,
  `hippo_reference/loader.py`, `ingestion/provenance.py`, `ingestion/pipeline.py`),
  cappella (5 files: `ingest/pipeline.py`, `adapters/{base,csv_adapter,json_adapter,sql_adapter}.py`),
  `tests/platform/` + `tests/contracts/` (~10 files). Python subpackage dir
  `canon/src/canon/hippo_reference/` may rename to `mosaic_reference/` (update the two
  entry-point values) — optional, recommended while the diff is open.
- CI `tests.yml`: install specs are path-based (`-e "./hippo[dev]"`) and keep working;
  update env vars to `MOSAIC_*` where used; renaming the `contracts-hippo-seam` job and
  `test_*_expects_hippo.py` filenames is **optional** (cosmetic — defer to WP-D6 if
  branch protection pins job names).
- Include WP-D3 edits here.
- **Acceptance:** full `tests.yml` matrix green; grep gate: no `import hippo` / `from
  hippo` left under `canon/src`, `cappella/src`, `tests/` (the *only* permitted `hippo`
  strings are paths (`./hippo`, `../hippo`), the legacy entry-point group, and §1.5
  carve-out identifiers).

**WP-D5 — Certification ledger + certify workflow.** *Depends on: WP-D4.*
- `certify.yml`: inputs `hippo_version`/`hippo_digest` → `mosaic_version`/`mosaic_digest`;
  `--component "hippo=..."` → `"mosaic=..."`; `HIPPO_IMAGE` → `MOSAIC_IMAGE`;
  compose file service/image refs in `certification/compose/`.
- `certification/ledger/`: new entries + tags use `mosaic` (`certified/aperture-X+mosaic-Y`);
  query/gate (`query.py`, `model.py`, `cli.py`) treats `hippo` and `mosaic` as the same
  component line (alias map) so historical entries stay queryable. **Never rewrite
  existing tags or `compatibility.json` history** (decision 1.7).
- **Acceptance:** `certification/tests/` green, incl. a new test: a pre-rename `hippo=`
  ledger entry and a post-rename `mosaic=` entry are the same component line.

**WP-D6 — Living-docs sweep (datahelix).** *Depends on: WP-D4 (do last).*
- Component name Hippo → Mosaic in **living** docs: `CLAUDE.md`, `README.md`,
  `platform/glossary.md`, `platform/overview.md`, `platform/architecture.md`,
  `platform/design/sec1–sec6`, `platform/design/domain-graph.md`,
  `platform/design/roadmap-1.0.md`, `platform/design/INDEX.md` prose, `mkdocs.yml` nav
  *titles* (paths stay per decision 1.6).
- **Do not** edit historical documents: `proposals/` (incl. this one's peers), ADR texts,
  dated session notes, `FABLE_HANDOFF.md`. Where a living doc cites history, "Hippo
  (now Mosaic)" on first mention is the pattern.
- **Acceptance:** `mkdocs build --strict` green; grep for `Hippo` in living docs returns
  only deliberate first-mention parentheticals.

### Phase A — aperture repo

**WP-A1 — Aperture dependency + docs touch-up.** *Depends on: Phase H merged.*
- `pyproject.toml`: `local = ["hippo"]` → `local = ["datahelix-mosaic"]`; description
  "…domain graph (Hippo)" → "(Mosaic)".
- Living docs (`CLAUDE.md`, `design/vision.md`, `design/architecture.md`): component
  name; ADR texts stay historical (ADR-0003 "config-is-linkml-in-hippo" keeps its slug
  and body; a one-line editor's note pointer is permitted, not required).
- **Acceptance:** aperture suite green; `uv pip install -e ".[local]"` resolves against
  a checkout of renamed mosaic (path pin in dev).

### Phase R — repository rename (admin; do last)

**WP-R1 — `BU-Neuromics/hippo` → `BU-Neuromics/mosaic`.** *Depends on: everything above
merged and settled.*
- GitHub repo rename (Settings → owner action; GitHub redirects old URLs and git
  remotes indefinitely, but update references anyway).
- datahelix: `.gitmodules` URL → `.../mosaic.git` (`git submodule sync`); **submodule
  mount path may stay `hippo/`** — moving it to `mosaic/` is a separate optional commit
  that must atomically update `mkdocs.yml` paths, `tests.yml` install paths/PYTHONPATH,
  cappella's uv-source path, and this repo's CLAUDE.md layout diagram. Decide at
  execution time; default = defer.
- Update org/repo references in living docs and issue templates.

---

## 3. Dependency graph

```
WP-H1..H6 (hippo PR) ──────────────┬──► WP-D4 (+D3) ──► WP-D5 ──► WP-D6 ──► WP-R1
                                   └──► WP-A1
WP-D1 (metapackage)  ── independent ──────────────────────────────────┘ (merge any time)
WP-D2 (canon dual-reg) ─ independent, safe before or after H
```

---

## 4. Things that explicitly do **not** change

- **LinkML schema vocabulary:** `hippo_core`, `hippo_ext` schema names; annotation keys
  (`hippo_index_partial`, `hippo_search`, …). These appear in *user schemas* — renaming
  them is a data-contract migration, out of scope (future ADR if ever).
- **SQL / on-disk identifiers:** `hippo_meta` table, existing deployments' DB filenames,
  provenance log content.
- **Ledger history:** existing `certified/aperture-X+hippo-Y` tags and `hippo=` entries.
- **`design/` histories** in all repos (ADRs, dated handoffs, session notes, proposals).
- **Submodule mount path `hippo/`** and everything keyed to it (until/unless WP-R1's
  optional path move).
- **PTS/issue keys, git history, tags.**

---

## 5. Rollback

- Phase H is one revertible PR; the shim means no consumer ever depended on the new
  names before WP-D4, so reverting H before D4 merges is zero-impact.
- WP-D4 is a single commit (submodule pointer + imports) — revert restores the old pin
  and old imports; canon's dual registration (D2) is harmless either way.
- WP-D1 (metapackage) is additive — revert deletes a directory.
- Point of no return is **WP-R1** (repo rename) — and even that is GitHub-redirected.

---

## 6. Order of operations summary

```
H.  hippo PR: rename + shims + dual groups + fallbacks + docs  (hippo#113)
D1. metapackage (parallel, any time)                           (datahelix#47)
D2. canon dual-registration (parallel, any time)               (datahelix#47)
--- merge H to hippo main ---
D4. submodule bump + consumer imports + D3 cappella retarget   (datahelix#47)
A1. aperture extra rename (parallel with D4)
D5. certification ledger/workflow alias
D6. living-docs sweep + optional cosmetic renames
R1. GitHub repo rename + .gitmodules (admin)
```

Estimated effort: H is the big one (~1 focused agent session, mechanical but wide);
D1/D2/A1 are small; D4 is medium and must land as one PR; D5/D6 small; R1 is minutes of
admin plus one small PR.
