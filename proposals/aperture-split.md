# Splitting Aperture out of `DataHelix` into its own repository

**Status:** ✅ **Executed 2026-06-13.** The seed repo was built, pushed to
`BU-Neuromics/aperture` (made public; CI green at seed commit `cbcd1c7`), and `DataHelix`
was cut over: `aperture/` is now a submodule pinned to the seed. CI/docs/mkdocs were
updated in the same change. The runbook below is retained as the historical record;
divergences from execution are noted inline (visibility, docs-symlink layer, PR-based
cutover).
**Goal:** Stand up a standalone `BU-Neuromics/aperture` repository for the **config-driven
portal** vision (see `aperture/design/portal-vision-handoff.md`), then re-attach it to
`DataHelix` as a git submodule so cross-component tests under `tests/platform/` and
`tests/contracts/` keep working without code changes.
**Template:** `proposals/hippo-split.md` (executed 2026-05-25). This split is **simpler**
than Hippo's and deliberately diverges — see §0.1.
**Non-goal:** Splitting out Canon, Cappella, or Bridge — those follow later.

---

## 0. Current state (verified 2026-06-13)

- Working on the prep branch `claude/fetch-artifacts-claude-chats-hn2pqn`.
- `aperture/` is a **real in-tree directory** (not yet a submodule), ~1,400 LOC of
  CLI-first v0.1 code under `src/aperture/`.
- **History is effectively non-existent:** exactly **1 commit** touches `aperture/`, and
  it is labeled `refactor(hippo): …` — the whole tree was dropped in as part of a bulk
  commit. (Contrast Hippo: 170 of 270 commits.) **There is no Aperture history worth
  preserving**, which is why this split skips `git filter-repo` entirely.
- **No test imports `aperture`.** `tests/platform/test_cli_integration.py` and
  `test_cross_component.py` only *simulate* `datahelix` by calling `HippoClient` directly; the
  `aperture/src` entries in `tests/conftest.py` and `test_cli_integration.py` PYTHONPATH
  are **vestigial**. Dropping the CLI breaks zero tests.
- `backends/` coupling: `src/aperture/backends/factory.py` imports
  `aperture.config.settings.ApertureConfig`. So the carry-set is **`backends/` + the
  `ApertureConfig` model it depends on**, not `backends/` alone (see §2.B).
- CI (`.github/workflows/tests.yml`): installs `aperture/[dev]` (line ~82) and puts
  `aperture/src` on the `platform`-job PYTHONPATH (lines ~86, ~91).
- `mkdocs.yml`: an `aperture/` nav block referencing `aperture/docs/{introduction,
  quickstart,cli-reference}.md` and `aperture/design/sec1..sec6`. **These CLI docs will
  not exist in the fresh-start submodule** — mkdocs `--strict` will break unless the nav
  is updated at cutover (see §2.D.3).

### 0.1 Why this diverges from the Hippo runbook

| | Hippo split | Aperture split |
|---|---|---|
| History to preserve | 170 woven commits | 1 mixed commit (none worth keeping) |
| Mechanic | `git filter-repo --subdirectory-filter` | **Seed a fresh repo** (no filter-repo) |
| Content | Move entire `hippo/` tree | **Fresh start**: carry only `backends/` (+ its config dep) and portal design docs; **drop the CLI** |
| Tests broken by content drop | n/a | **none** (no test imports aperture) |

---

## 1. Decisions (locked — confirmed with user 2026-06-13)

| # | Question | Decision | Notes |
|---|---|---|---|
| 1.1 | New GitHub org/repo name | **`BU-Neuromics/aperture`** | Matches the Hippo submodule convention. |
| 1.2 | Carry CLI v0.1 code or fresh start | **Fresh start** | Keep only `src/aperture/backends/` (+ `ApertureConfig`); CLI v0.1 superseded by the portal vision. |
| 1.3 | Submodule pin strategy | **Pin to commit** | `git submodule update --remote && git commit` is the "bump aperture" motion (matches Hippo 1.2). |
| 1.4 | Initial submodule pin | **Initial portal commit on `main`** | No meaningful tags yet; tag `v0.1.0-portal` optional at first green CI. |
| 1.5 | Own mkdocs site for the new repo? | **No (for now)** | DataHelix keeps the unified docs site; aperture repo ships docs source only (matches Hippo 1.6). |

### 1.1 Open sub-decisions (confirm at execution, low-stakes)

- **CLI v0.1 archival:** the CLI code + `sec1..sec6` design remain in DataHelix history at
  the pre-split commit. Default: **leave in history, link from the split commit message**;
  do *not* copy into the new repo. (Alternative: copy into new repo under
  `design/archive/cli-v0.1/` if you want it browsable there.)
- **Package name:** keep distribution name `bass-aperture` (import package `aperture`),
  or rename. Default: **keep** `bass-aperture` / `aperture`.

---

## 2. Migration phases

Each phase is independently reviewable. Nothing in §2.C+ runs until §1 is confirmed and
the new repo exists.

### Phase A — Pre-flight (in `DataHelix`, this prep session — DONE / TODO)

- [x] A1. Land the portal handoff verbatim at `aperture/design/portal-vision-handoff.md`.
- [x] A2. Capture proposed §9 resolutions at `aperture/design/portal-open-questions.md`.
- [x] A3. Update `aperture/design/INDEX.md` with the direction-change banner + doc map.
- [x] A4. Write this runbook.
- [ ] A5. (Execution session) Confirm §1 decisions still hold; confirm write scope on
      `BU-Neuromics/aperture`.

### Phase B — Build the fresh `aperture` repo seed

Done in a scratch directory; this is a **curated copy**, not a history rewrite.

```bash
# 1. Scratch dir for the new repo
mkdir -p /tmp/aperture-seed && cd /tmp/aperture-seed && git init -b main

# 2. Carry the reusable backend protocol + its config dependency.
#    factory.py imports aperture.config.settings.ApertureConfig, so bring that model too.
mkdir -p src/aperture/backends src/aperture/config
cp -r <DataHelix>/aperture/src/aperture/backends/.        src/aperture/backends/
cp    <DataHelix>/aperture/src/aperture/config/settings.py src/aperture/config/
cp    <DataHelix>/aperture/src/aperture/__init__.py        src/aperture/__init__.py
touch src/aperture/config/__init__.py
#    Then PRUNE config/settings.py to the fields backends/ actually needs (drop CLI-only
#    settings), and verify nothing else from the CLI tree is referenced:
grep -rn "aperture.cli\|aperture.models\|config.defaults" src/aperture/  # expect: empty

# 3. Carry the portal design docs (the reason for the fresh start).
mkdir -p design
cp <DataHelix>/aperture/design/portal-vision-handoff.md design/
cp <DataHelix>/aperture/design/portal-open-questions.md design/
#    Write a fresh design/INDEX.md scoped to the portal (no CLI sec1..sec6 carryover).

# 4. New pyproject.toml (drop the `datahelix` CLI script + typer; see §2.B.4 draft).
# 5. README.md describing the portal (not the CLI).
# 6. LICENSE — copy from DataHelix (MIT).
cp <DataHelix>/LICENSE .
# 7. .github/workflows/tests.yml for the new repo (see §2.B.7 draft).

git add -A
git commit -m "feat: seed Aperture portal repo (backends protocol + portal design)

Fresh start from the DataHelix monorepo. Carries the reusable Hippo backend
protocol and the config-driven portal design handoff; the CLI-first v0.1
implementation is intentionally left behind in DataHelix history."
```

#### §2.B.4 — Draft `pyproject.toml` (portal seed)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bass-aperture"
version = "0.1.0"
description = "DataHelix Aperture - config-driven data portal over Hippo"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
    "httpx>=0.24",
    "pydantic>=2.0",
    "pyyaml",
]

[project.optional-dependencies]
local = ["bass-hippo"]
dev = ["pytest>=7.0", "pytest-cov"]

# NOTE: no [project.scripts] `datahelix` entry — the CLI is superseded.
# Web/portal + component-runtime deps will be added as the portal is built.

[tool.hatch.build.targets.wheel]
packages = ["src/aperture"]
```

#### §2.B.7 — Draft `.github/workflows/tests.yml` (new aperture repo)

```yaml
name: Tests
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
concurrency:
  group: tests-${{ github.ref }}
  cancel-in-progress: true
jobs:
  aperture:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}" }
      - run: uv pip install --system -e ".[dev]"
      - run: pytest -v
```

### Phase C — Publish the new repo

```bash
# C1. Create BU-Neuromics/aperture on GitHub (empty, public, wiki disabled).
#     Requires GitHub scope on BU-Neuromics — set up the execution session accordingly.
# C2. Push the seed:
cd /tmp/aperture-seed
git remote add origin https://github.com/BU-Neuromics/aperture.git
git push -u origin main
# C3. Confirm CI goes green on main before the DataHelix cutover.
# C4. (Optional) tag v0.1.0-portal.
```

### Phase D — Replace `aperture/` in DataHelix with a submodule

A **single DataHelix commit** so the tree is never half-state.

```bash
cd <DataHelix>
git checkout main && git pull        # (or the designated integration branch)

# 1. Remove the in-tree directory
git rm -r aperture

# 2. Add submodule pinned to the seed commit
git submodule add https://github.com/BU-Neuromics/aperture.git aperture
cd aperture && git checkout <seed-commit-or-tag> && cd ..
git add aperture .gitmodules

# 3. CI + docs edits (see §2.D.3), then git add them.

# 4. Single commit + push
git commit -m "chore: replace aperture/ subtree with submodule (BU-Neuromics/aperture)

Aperture is now a standalone repo for the config-driven portal vision. The
CLI-first v0.1 implementation remains in DataHelix history at the parent commit;
the submodule carries only the reusable backend protocol and portal design.
No test imports aperture, so platform/contract suites are unaffected."
git push
# 5. Watch the Tests + docs workflows on the pushed ref — green = cutover complete.
```

#### §2.D.3 — CI + docs changes in DataHelix

In `.github/workflows/tests.yml`:
- The `platform`-job checkout must become submodule-aware:
  ```yaml
  - uses: actions/checkout@v4
    with:
      submodules: recursive
  ```
- The `uv pip install -e "aperture/[dev]"` step: the submodule still has a
  `pyproject.toml`, so this keeps working. (Optional: drop it if no DataHelix test needs
  the aperture package installed — none import it today.)
- The `aperture/src` PYTHONPATH entries are now vestigial but **harmless** (the submodule
  mounts `src/aperture/backends` back at the same path). Leave or remove; if removed, also
  drop `aperture/src` from `tests/conftest.py` (line ~25) and
  `tests/platform/test_cli_integration.py` (line ~18).

In `.github/workflows/docs.yml`:
- Add `submodules: recursive` to the checkout.

In `mkdocs.yml` — **required**, or `mkdocs build --strict` fails:
- Replace the `aperture/` nav block. The CLI pages (`aperture/docs/introduction.md`,
  `quickstart.md`, `cli-reference.md`) and `aperture/design/sec1..sec6` **will not exist**
  in the fresh-start submodule. Point the nav at what the submodule actually ships:
  ```yaml
  - Aperture:
      - Portal Vision (Handoff): aperture/design/portal-vision-handoff.md
      - Open Questions: aperture/design/portal-open-questions.md
  ```
  (Expand as the new repo grows its `docs/`.)

### Phase E — Cleanup (after cutover is green)

- E1. Optionally retire/rename the now-misleadingly-named
  `tests/platform/test_cli_integration.py` (it tests the Hippo/Canon path, not a CLI).
  Low priority; it still passes.
- E2. Update DataHelix `README.md` to note `aperture` is a submodule and link the repo.
- E3. `CLAUDE.md` already describes the submodule pattern; add `aperture` alongside
  `hippo` in the components list if it enumerates which are split.

---

## 3. Things that explicitly do **not** change

- **Tests under `tests/platform/` and `tests/contracts/`:** no file imports `aperture`,
  so imports, `PYTHONPATH`, and behavior are unchanged. The submodule mounts at the same
  `aperture/` path.
- **DataHelix commit SHAs before the split:** untouched. `git rm -r aperture` + add-submodule
  is a normal forward commit; DataHelix history is not rewritten.
- **CLI v0.1 source + `sec1..sec6` design:** preserved in DataHelix history at the pre-split
  commit (decision 1.1 default: not copied into the new repo).

---

## 4. Rollback plan

If something goes wrong after Phase D but before building on the new layout:
1. Revert the "replace aperture/ subtree with submodule" commit on DataHelix — `aperture/`
   reappears verbatim (CLI v0.1 and all).
2. The new `BU-Neuromics/aperture` repo can sit unused; it's a fresh copy, not a move.
The point of no return is only if/when CLI history is later pruned — which this plan does
not do.

---

## 5. Order of operations summary

```
A. Pre-flight in DataHelix (this session: land handoff + design docs + this runbook)
B. Build fresh aperture seed (backends/ + ApertureConfig + portal design + pyproject/CI)
C. Create BU-Neuromics/aperture, push seed, confirm CI green
D. DataHelix commit: rm aperture/ + add submodule + CI/mkdocs edits (single commit)
E. Cleanup: docs/README touch-ups; optional test rename
```

Total work: ~1 focused session in an environment scoped to both `DataHelix` and
`BU-Neuromics/aperture`.
