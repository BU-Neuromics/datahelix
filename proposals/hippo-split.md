# Splitting Hippo out of `drylims` into its own repository

**Status:** ✅ **Executed 2026-05-25** — commits `8a58c61` (plan) through `a614fc7` (README/CLAUDE.md update) on drylims `main`; cutover at `7cfab61`; CI fix at `7a7ca1f`. New repo: https://github.com/BU-Neuromics/hippo. Migrated PRs: BU-Neuromics/hippo#1/#2/#3 (stacked). Drylims origin now has only `main` and `gh-pages`. This document is historical — do not re-run.
**Goal:** Extract `hippo/` from the `drylims` monorepo into a standalone GitHub repository with full git history preserved, then re-attach it to `drylims` as a git submodule so cross-component integration tests under `tests/platform/` and `tests/contracts/` keep working without code changes.
**Non-goal:** Splitting out Canon, Cappella, Aperture, or Bridge — those follow later, using this migration as the template.

---

## 0. Current state (verified)

- Working tree clean on `pts-255/entityref-loadresult-v2`.
- `hippo/` is structurally self-contained: own `pyproject.toml` (name=`hippo`, version `0.6.0`), Dockerfile, `tests/`, `CLAUDE.md`, `openspec/`, `plan/`, `CHANGELOG.md`.
- 170 of 270 commits in the repo touch `hippo/`. Cross-cutting commits are mostly generated `site/` output and shared infra (`mkdocs.yml`, `.github/workflows`) — no commits weave hippo source into other component source.
- Tags `v0.1.0`–`v0.6.0` track hippo de-facto (hippo dominates the commit log); `hippo-v0.3.1` already uses the prefixed scheme.
- In-flight branches with hippo work in this repo:
  - `pts-243/reference-loader-v2-design` (pushed to `origin`)
  - `pts-255/entityref-loadresult-v2` (current, pushed to `origin`)
  - Plus several merged-but-unpruned `pts-2xx-*` branches on `origin`.
- CI (`.github/workflows/tests.yml`) has `hippo:`, `hippo-postgres:`, and a `platform:` job that depends on hippo, canon, cappella, aperture being mounted at their current paths via `PYTHONPATH`.
- `mkdocs.yml` references `hippo/docs/...` paths; docs build is currently `mkdocs build --strict` from drylims root.

---

## 1. Decisions (locked)

| # | Question | Decision | Notes |
|---|---|---|---|
| 1.1 | New GitHub org/repo name | **`BU-Neuromics/hippo`** | Confirmed by user 2026-05-25. |
| 1.2 | Submodule pin strategy | **Pin to commit** | `git submodule update --remote && git commit` is the explicit "bump hippo" motion in drylims. (Default accepted.) |
| 1.3 | Initial submodule pin | **Tag `v0.6.0`** | Confirmed by user 2026-05-25. |
| 1.4 | Tags `v0.1.0`–`v0.6.0` on `drylims` | **Keep** | Point at real drylims commits; also reproduced in new hippo repo (duplication OK). Default accepted. |
| 1.5 | In-flight branches `pts-243`, `pts-255` on drylims `origin` | **Delete after cutover** | After PRs are reopened against the new hippo repo. Default accepted. |
| 1.6 | New hippo repo: own mkdocs site? | **No (for now)** | Drylims keeps the unified docs site; hippo repo ships docs source only. Revisit at canon/cappella split. |
| 1.7 | Move `tests/contracts/test_hippo_self_contract.py` into hippo before filter | **Yes** | Confirmed by user 2026-05-25. Moves into `hippo/tests/contracts/test_self_contract.py` as part of Phase A so history transfers cleanly. The other `tests/contracts/test_*_expects_*.py` files stay in drylims. |

---

## 2. Migration phases

Each phase is independently reviewable. Nothing in §3+ runs until §1 decisions are confirmed.

### Phase A — Pre-flight (no code changes yet)

A1. Confirm §1 decisions with user.
A2. Verify no uncommitted/unpushed work on any hippo-touching branch locally.
A3. Open any in-flight hippo PRs in `drylims` — note their numbers; they will be closed and reopened against the new hippo repo with a comment explaining the move.
A4. Move the self-contract test into hippo's tree (decision 1.7) directly on `main` (no PR; user is sole maintainer):
```bash
git checkout main && git pull
git mv tests/contracts/test_hippo_self_contract.py hippo/tests/contracts/test_self_contract.py
# adjust sys.path insertion (~line 20) from
#   _root = Path(__file__).parent.parent.parent
#   sys.path.insert(0, str(_root / "hippo/src"))
# to
#   _root = Path(__file__).parent.parent.parent  # hippo repo root after split
#   sys.path.insert(0, str(_root / "src"))
# Sanity-check from drylims root that the test still resolves the import pre-split:
PYTHONPATH=hippo/src pytest hippo/tests/contracts/test_self_contract.py -q
git commit -m "chore(hippo): move self-contract test into hippo/tests in prep for repo split"
git push origin main
```
Note: pre-split the path is `_root.parent.parent.parent` → drylims root → `hippo/src` works. Post-split, the same expression resolves to the hippo repo root, and `src` is the correct subdir. So we change the *suffix only* (`hippo/src` → `src`). The `_root` chain still walks three parents because the file moves to `hippo/tests/contracts/` and after split lives at `tests/contracts/`, both of which are three levels deep relative to their respective repo roots.
A5. Confirm `pts-255` and any other in-flight branches are merged or in a recoverable state in the new hippo repo (they'll appear there post-filter — verify they look right before deleting from drylims).

### Phase B — Extract `hippo/` into a standalone repo with full history

Done on a **fresh clone**, never the working repo, to keep filter-repo's destructive rewrite isolated.

```bash
# 1. Fresh clone for the rewrite
cd /tmp
git clone --no-local /home/admin/.openclaw/workspace/drylims-docs hippo-extract
cd hippo-extract
git remote remove origin   # safety: prevent accidental push to drylims

# 2. Fetch any unfetched refs from upstream (so all branches are preserved)
cd /home/admin/.openclaw/workspace/drylims-docs && git fetch --all --tags
cd /tmp/hippo-extract && git fetch /home/admin/.openclaw/workspace/drylims-docs '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'

# 3. Rewrite: keep only commits touching hippo/, flatten paths
pip install git-filter-repo  # or: brew install git-filter-repo
git filter-repo --subdirectory-filter hippo/

# 4. Verify
git log --oneline | wc -l       # expect ~170
git tag                         # expect v0.1.0..v0.6.0, hippo-v0.3.1
ls                              # expect: src/, tests/, pyproject.toml, etc. (no "hippo/" prefix)
test -f pyproject.toml && grep '^name' pyproject.toml   # expect: name = "hippo"

# 5. Add LICENSE (filter-repo dropped the root LICENSE)
# Copy drylims/LICENSE in; commit as a new commit on main.
cp /home/admin/.openclaw/workspace/drylims-docs/LICENSE .
git add LICENSE
git commit -m "chore: add LICENSE (carried from drylims monorepo)"

# 6. Write the new repo's own CI (don't try to filter the monorepo's tests.yml)
# Create .github/workflows/tests.yml with the hippo + hippo-postgres jobs,
# but without "working-directory: hippo" (now repo root).
# Draft below in §2.B.6.
```

#### §2.B.6 — Draft `.github/workflows/tests.yml` for new hippo repo

```yaml
name: Tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
concurrency:
  group: tests-${{ github.ref }}
  cancel-in-progress: true

jobs:
  hippo:
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
      - run: pytest -v --ignore=tests/integration/test_postgres_adapter.py

  hippo-postgres:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: hippo_test, POSTGRES_PASSWORD: hippo_test, POSTGRES_DB: hippo_test }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U hippo_test" --health-interval 10s
          --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: uv pip install --system -e ".[dev,postgres]"
      - env: { HIPPO_DATABASE_URL: postgresql://hippo_test:hippo_test@localhost:5432/hippo_test }
        run: pytest tests/integration/test_postgres_adapter.py -v
```

### Phase C — Publish the new repo

C1. `BU-Neuromics/hippo` already created (2026-05-25) — empty, public, wiki disabled.
C2. Push from the filtered clone:
```bash
cd /tmp/hippo-extract
git remote add origin https://github.com/BU-Neuromics/hippo.git
git push origin --all
git push origin --tags
```
C3. Browse repo on GitHub: confirm tags, branches, recent commits look correct.
C4. Optional (not required since user is sole maintainer): enable branch protection on `main`, add `hippo` and `hippo-postgres` status checks as required.

### Phase D — Replace `hippo/` in drylims with a submodule

This is a **single drylims commit** directly on `main` (no PR) so the tree is never half-state.

```bash
cd /home/admin/.openclaw/workspace/drylims-docs
git checkout main && git pull

# 1. Remove the directory (git rm cleans index)
git rm -r hippo

# 2. Add submodule pinned to v0.6.0 (per decision 1.3)
git submodule add https://github.com/BU-Neuromics/hippo.git hippo
cd hippo && git checkout v0.6.0 && cd ..
git add hippo .gitmodules

# 3. Update CI: submodule-aware checkouts (affects platform: and docs: jobs)
#    See §2.D.3 for the diff. Edit those files, then `git add`.

# 4. Single commit + push
git commit -m "chore: replace hippo/ subtree with submodule pointing at hippo@v0.6.0

Hippo now lives at github.com/BU-Neuromics/hippo with its own
version, commit, and issue history. Cross-component integration tests under
tests/platform/ and tests/contracts/ continue to import from hippo/src/...
unchanged, because the submodule mounts at the same path."
git push origin main

# 5. Watch the `Tests` workflow run on origin/main — green means cutover complete.
```

#### §2.D.3 — CI changes in drylims

In `.github/workflows/tests.yml`:
- **Delete** the `hippo:` and `hippo-postgres:` jobs (they live in the hippo repo now).
- For the `platform:` job (the one that uses `PYTHONPATH: hippo/src:canon/src:...`), change `actions/checkout@v4` to:
  ```yaml
  - uses: actions/checkout@v4
    with:
      submodules: recursive
  ```
- The `cappella:` and `canon:` jobs are unchanged.

In `.github/workflows/docs.yml`:
- Change the single `actions/checkout@v4` to include `submodules: recursive` (mkdocs build reads `hippo/docs/`).

### Phase E — Cleanup on drylims (after PR merges)

E1. Delete merged in-flight branches from `origin` (decision 1.5):
```bash
git push origin --delete pts-243/reference-loader-v2-design pts-255/entityref-loadresult-v2
# plus the older merged-but-unpruned pts-2xx-* branches
```
E2. Local branch cleanup: `git branch -D` for any local hippo-touching branches; future hippo work happens in the hippo repo clone.
E3. Update `CLAUDE.md` at drylims root: it currently says "documentation-only repository" but actually has source under `hippo/`, `canon/`, etc. After the split, the statement becomes "drylims is the platform integration repo — component source lives in submodules under each component directory." (Out of scope for the migration itself, but worth flagging.)
E4. Update top-level `README.md` to note the new submodule layout and link to the hippo repo.

---

## 3. Things that explicitly do **not** change

- **PTS-NNN issue keys**: they live in Paperclip, not git. The hippo repo can keep referencing the same `PTS-` namespace, or you can carve out a new sub-project; that decision is decoupled from the repo split.
- **Tests under `tests/platform/` and `tests/contracts/`** (except the moved self-contract): file paths, imports, and `PYTHONPATH` entries are unchanged because the submodule mounts hippo's contents back at `hippo/`.
- **drylims commit SHAs** that existed before the split: untouched. drylims history is not rewritten; the `git rm -r hippo` + add-submodule is a normal forward commit.
- **`hippo/CHANGELOG.md`**: carried over by `filter-repo` along with everything else inside `hippo/`.

---

## 4. Rollback plan

If something goes wrong after Phase D merges but before users have built on the new submodule layout:
1. Revert the "chore: replace hippo/ subtree with submodule" commit on drylims. `hippo/` reappears verbatim.
2. New hippo repo can sit unused; revisit when ready.
The new hippo repo is non-destructive to create — it's a copy, not a move at the GitHub level. The point of no return is only when you delete branches from drylims `origin` in Phase E.

---

## 5. Order of operations summary

```
A. Pre-flight (drylims commits: move self-contract test if 1.7=yes)
B. Filter-repo run on fresh clone of drylims
C. Push to new GitHub repo + reopen in-flight PRs there
D. Drylims PR: rm hippo/ + add submodule + CI tweaks (single commit)
E. Cleanup: delete dead branches on drylims origin
```

Total work: ~1 focused session if §1 decisions are all yeses on the recommended defaults.
