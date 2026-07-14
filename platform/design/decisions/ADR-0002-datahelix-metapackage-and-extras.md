# ADR-0002: Distribute the platform as a `datahelix` metapackage with per-component extras

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** labadorf, design session (packaging & naming, 2026-07-08)
- **Related:** `sec2_components.md` (the optional/non-optional component matrix); ADR-0001 (certified-frontier ledger — version pinning this rides on); **Hippo ADR-0004** (rename Hippo → Mosaic — the first beneficiary of prefixed dist names); component `pyproject.toml` files (`hippo`, `canon`, `cappella`, `datahelix-aperture`)

## Context

The platform ships as several **independently-versioned components** — Mosaic (the LinkML runtime, née Hippo), Canon, Cappella, Aperture, Bridge — some of them git submodules with their own release cadence (ADR-0001). Each publishes, or will publish, a Python distribution. Today those dist names are **bare and inconsistent**: `hippo`, `canon`, `cappella` are unprefixed, while Aperture already ships as `datahelix-aperture` (import stays `aperture`).

Three problems follow from the status quo:

1. **PyPI collision.** Bare component names sit in a crowded namespace — `hippo` in particular is heavily squatted, and there is no reason to expect the next component name to be free either.
2. **No single entry point.** There is no one memorable, brandable thing a user `pip install`s to get "the platform." They must discover each component's dist name individually.
3. **Optionality is invisible.** `sec2_components.md` classifies exactly one component — Mosaic — as non-optional ("platform foundation"); the rest are optional. Nothing in the install surface communicates that.

The constraints that bound any fix: components must keep **shipping independently** (ADR-0001 certifies exact version *pairs*, not a monolith); the platform is **SDK-first** (business logic lives in components, never in a distribution shell); and the fix must not collapse the submodule architecture into one release train.

The question this ADR settles: *how do we give the platform one branded, collision-free install surface without merging the independently-versioned components into a monolith?*

## Decision

The platform will be distributed as a **thin `datahelix` metapackage** whose **extras** pull in per-component distributions. `datahelix` is unregistered on PyPI (verified 404) and is claimed for this purpose.

1. **Prefixed component dists, bare imports (Layout A).** Components publish as `datahelix-mosaic`, `datahelix-canon`, `datahelix-cappella`, `datahelix-aperture` (already), `datahelix-bridge`. **Import names stay bare** (`import mosaic`, `import canon`). Import-namespace packages (`datahelix.<component>` via PEP 420) are **explicitly deferred** — they are a larger refactor and are incompatible with the metapackage shipping its own top-level module (see Alternatives).

2. **Bare install pulls the core.** `datahelix` hard-depends on the non-optional foundation (`datahelix-mosaic`), so `pip install datahelix` yields a working typed graph + SDK + CLI. Optional components are extras — `datahelix[canon]`, `[cappella]`, `[aperture]`, `[bridge]`, and an aggregate `[all]` — mapping one-to-one onto the sec2 optional/non-optional matrix.

3. **The metapackage stays thin.** Its only jobs are: (a) **own the version-compatibility matrix** — a `datahelix` release *is* a platform release, pinning tested component ranges; (b) a **small umbrella CLI** (`datahelix info` / `doctor`) reclaiming the `datahelix` command Aperture's `pyproject.toml` records as "superseded", doing introspection only (what's installed, versions, health); (c) optional **convenience re-exports** (e.g. `from datahelix import MosaicClient`). No entity, storage, or transform logic ever lives here.

4. **Ranged pins, coordinated with the ledger.** Extras pin **compatible ranges** (`~=`, `>=x,<y`), never exact versions — the metapackage is another consumer of the certified pairs from ADR-0001, not a second matrix. A component patch must not force a metapackage re-release.

## Consequences

- **One branded, collision-free install surface.** `pip install datahelix[all]` is the whole platform; the crowded bare-name namespace is no longer touched. This **removes PyPI saturation as a forcing function for component names** — unblocking Hippo → Mosaic (ADR-0004) as a pure naming-fit decision rather than a necessity.
- **Bare install is useful, not an empty shell.** `pip install datahelix` runs — it is the core graph, matching how Jupyter installs a usable stack.
- **Name insulation.** A component's identity word (`mosaic`, `canon`, …) now surfaces only as an extra key, a prefixed dist, and a bare import — none of which require global PyPI uniqueness.
- **New obligations on components:** publish under `datahelix-<name>`; keep import names bare for now.
- **New obligations on the datahelix repo:** own the metapackage (version matrix + umbrella CLI), and treat a metapackage release as a coordination point — which rides the **existing** submodule-bump workflow rather than adding a new one.
- **Sits atop ADR-0001:** metapackage pins should be drawn from certified pairs; exact-pinning here would fight the ledger and make releases brittle.

## Alternatives considered

- **Status quo — bare, unprefixed per-component dists.** Collide with PyPI, offer no unified entry point, and force users to learn each dist name. Rejected.
- **Monolithic `datahelix` distribution that vendors all component code**, with extras gating only third-party deps (the `pandas[excel]` shape). Fights independent versioning, the submodule architecture, and SDK-first; couples all release cadences into one train. This is precisely the failure mode that led **Google Cloud and Azure to deprecate their all-in-one umbrella metapackages**. Rejected.
- **Import-namespace packages now** (`datahelix.mosaic`, `datahelix.canon` via PEP 420). Cleaner branding, but a much larger refactor: it rewrites every import *and* the cross-package entry-point group names, and the metapackage could no longer ship its own `datahelix/__init__.py` / umbrella CLI without shadowing the namespace. **Deferred, not rejected** — revisit once the rename settles.
- **Empty-shell bare install** (every component an extra; `datahelix` alone installs nothing usable). User-hostile — the exact frustration of the retired Google/Azure umbrellas. Rejected in favor of bare-install-pulls-core.

## Notes / open sub-questions

- **Prior art that works:** `jupyter` (metapackage → `notebook`/`ipykernel`/`nbconvert`), `apache-airflow[postgres,celery]` → `apache-airflow-providers-*`, the LangChain `langchain`/`-core`/`-community` split, the OpenTelemetry distro. **Cautionary:** Google Cloud (`google-cloud`) and Azure (`azure`) both retired monolithic umbrellas — the lesson baked into this ADR is *thin + curated + useful-by-default + ranged pins*.
- Confirm the exact extra set and whether `[all]` includes Bridge by default (Bridge is required only for multi-user).
- Specify the umbrella CLI surface (`info` / `doctor` / `--version`) — introspection over installed component entry points, no domain logic.
- **Migration:** rename the existing dists (`hippo` → `datahelix-mosaic` per ADR-0004, `canon` → `datahelix-canon`, `cappella` → `datahelix-cappella`); stand up the `datahelix` metapackage in this repo.
