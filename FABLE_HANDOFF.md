# BASS Platform — Autonomous Development Handoff for Fable

**Audience:** Fable, operating as an autonomous developer on the BASS platform.
**Repo:** `drylims` (platform integration repo) — https://github.com/VA-NCPTSDBB-Bioinformatics/drylims
**Prepared:** 2026-06-11. **Ground-truth basis:** all maturity/test claims below were verified by running the suites and reading the specs on this date against `hippo@18935c5` (v0.8.0).

---

## 0. How to use this document

This is your orientation and charter. It tells you **what BASS is**, **why it exists**, **what's actually built vs. designed**, **how to find the next unit of work**, and **the ambitious milestones you should drive toward**. It does not replace the design specs — it points you into them. When this document and a design spec disagree, **the design spec wins** and you should flag the drift.

Read in this order before writing any code:
1. This handoff (you're here).
2. `proposals/biodms2026/` — the grant proposal. The *why*. Non-negotiable framing.
3. `platform/design/sec1_overview.md` → `sec5_integration_test_strategy.md` — the cross-component architecture.
4. The `design/INDEX.md` of whichever component you're about to touch.
5. `TESTING.md` and `CLAUDE.md` (repo root) — conventions and the testing pyramid.

---

## 1. What BASS is

**BASS (Bioinformatics Analysis Software System)** is an open-source, modular **metadata-intelligence layer** for high-throughput biomedical data. It is the synthesis of ~two decades of building and re-analyzing biological pipelines, designed to kill five recurring failure modes that recur at every site, in every modality:

1. **Redundant storage of reprocessed artifacts** — the same FASTQ re-aligned with slightly different parameters, producing near-identical BAMs with unknown lineage.
2. **Lost provenance** — files accumulate with no record of which pipeline, code version, or inputs produced them (*"was this built against Ensembl 105 or 111?"* becomes unanswerable).
3. **Ad-hoc reimplementation** of standard cleaning operations, causing silent divergence across datasets.
4. **Inaccessible, unshareable metadata** — sample-to-file maps trapped in spreadsheets and LIMS behind institutional walls.
5. **Iteration without provenance** — no clean way to ship new versions of an analysis product alongside old ones without breaking links to published results.

**Primary deployment site:** the **National Center for PTSD Brain Bank** (300+ post-mortem donations; clinical histories, neuropathology, dissection records, tissue inventories, histology images, and high-throughput sequencing). It's the acutest possible target because all five failure modes become acute *simultaneously*, across modalities. The proposal's framing: multi-modal AI on this cohort is *"gated not on model capacity but on the absence of a trustworthy substrate that an agent or pipeline can query without bespoke connectors."*

**The vision, in one sentence (verbatim from the proposal):**
> "A metadata intelligence layer that is open-source, edited by domain experts rather than database engineers, provenance-rich by construction, deployable across scales, and structured so that AI agents can traverse and resolve it without bespoke connectors."

---

## 2. The three technical bets (the soul of the project)

Every design decision serves one of these. If a change you're considering weakens one of them, stop and reconsider.

**Bet 1 — LinkML schemas as runtime artifacts.** The schema is authored directly in **LinkML** and read *at runtime* by a config-driven relational engine. The same LinkML document drives (i) the physical tables and indexes (explicit columns, **not** EAV), (ii) the typed Python SDK, (iii) the REST API surface, (iv) write-path validation (referential integrity + CEL-expressible business rules), and (v) the migration plan when the schema changes. **Adding an entity type, field, or relationship is a configuration change, not a release.**

**Bet 2 — Provenance by default, at row level.** Every write records who changed what, when, and via which path, in an **append-only provenance log**. There are **no hard deletes**; lifecycle is an `is_available` flag whose transitions are themselves provenance events. `created_at` / `updated_at` / `schema_version` are **not** stored on the row — they're computed at read time from the provenance log. This inverts the usual "provenance as a sidecar audited only when something breaks."

**Bet 3 — AI-readiness by construction.** Two concrete mechanisms, not "we'll call an LLM somewhere":
   - **(a) DRS-resolvable entities.** Any entity — donor, sample, derived DESeq result, file — is addressable as `drs://host/uuid` via a GA4GH Data Repository Service endpoint. An agent (over MCP or equivalent) can traverse derivation chains, request the underlying artifact, and produce reproducible, citable answers without a per-source connector.
   - **(b) Semantic dependency resolution.** Instead of DAG scheduling over file paths, you state *what you want* ("an AlignmentFile for sample S001 against GRCh38 / Ensembl 111 with STAR 2.7.11a") and the platform either **REUSEs** a satisfying Hippo entity, **FETCHes** one via DRS, or **BUILDs** it by finding a production rule and recursively resolving inputs.

**SDK-first architecture.** All business logic lives in the Python SDK; REST/GraphQL are *thin transport wrappers*. Consequence: local laptop use (SQLite, no server) is exactly as capable as server mode. A REST endpoint can never expose something the SDK can't do. Keep this invariant.

---

## 3. Repository & component map

`drylims` is the **platform integration repo**: cross-cutting docs, the unified MkDocs site, and cross-component tests under `tests/platform/` and `tests/contracts/`. Component source lives in component directories — some in-tree, **Hippo is a git submodule**.

> **Submodule discipline (critical).** Hippo lives at [BU-Neuromics/hippo](https://github.com/BU-Neuromics/hippo), mounted at `hippo/`. Clone with `--recurse-submodules`. To bump it: `git submodule update --remote hippo`, run the contract + platform suites, then commit the pointer change **in its own dedicated PR** — never fold a hippo bump into an unrelated change. Other components are expected to split out the same way over time (see `proposals/hippo-split.md` for the template).

| Component | Role | Source | Version | Maturity (verified 2026-06-11) | Spec status |
|---|---|---|---|---|---|
| **Hippo** | Metadata store — the platform spine | submodule | **0.8.0** | **Well-developed** (~120 src files, 110+ test files; SDK, SQLite adapter, provenance, REST, CLI, TUI, validators, plugins) | v0.1 spec approved; LinkML redesign (sec9) approved 2026-04-18 and mid-rollout via OpenSpec waves |
| **Canon** | Semantic artifact resolver (REUSE/FETCH/BUILD) | in-tree | 0.1.0 | **Skeleton** (~38 files, 11 test files; resolver/rules/executors/storage scaffolded, cwltool-only) | **Design v0.2 complete**, well ahead of code |
| **Cappella** | Harmonization engine: external sources → Hippo | in-tree | 0.1.0 | **v0.1 implemented** (~31 files, 15 test files; generic CSV/JSON/XML/SQL adapters, trigger engine, upsert-by-ExternalID) | Design v0.1 complete; v0.2 (real LIMS adapters, reactive triggers) undesigned |
| **Aperture** | Interface layer (CLI now, web later) | in-tree | 0.1.0 (`bass-aperture`) | **Early CLI skeleton** (~23 files, 2 test files; Typer `bass` CLI, Hippo backends) | Design v0.1 (CLI) complete; **no openspec/plan decomposition yet** |
| **Bridge** | Optional auth gateway + cross-component sync | in-tree | — | **Design-only — zero code** (no `src/`, no `pyproject.toml`; only Dockerfile + nginx.conf) | Design v0.1 complete (6 sections + 6 user docs) |

There is also a **Canon** dependency on Hippo's reference-schema concepts (Tool, ToolVersion, GenomeBuild, GeneAnnotation, WorkflowRun). Dependency order is **Hippo → Canon → Cappella → Aperture → Bridge**; Bridge is off the critical path for v1.0 (everything works in single-user SDK mode without it).

---

## 4. Current state — what works *today* vs. what is designed

I verified the integration surface by running the cross-component suites against `hippo@18935c5` with `PYTHONPATH=hippo/src:canon/src:cappella/src:aperture/src` (the CI configuration):

- `tests/contracts/` → **108 passed**
- `tests/platform/` → **114 passed, 1 skipped**

So the following is **real, tested, and load-bearing** — treat it as the stable base you build on:

- Hippo SDK (`HippoClient`): entity CRUD, query, search, upsert-by-ExternalID, provenance recording; SQLite adapter; FastAPI REST surface; CLI; tiered write-path validation.
- Canon: rules DSL parsing, entity-reference resolution, recursive planner with cycle detection, cwltool executor, WorkflowRun provenance write-back.
- Cappella: generic config-driven adapters (CSV/JSON/XML/SQL), trigger engine framework, idempotent upsert.
- **Cross-component contracts**, each a consumer-driven behavioral spec: `test_canon_expects_hippo.py`, `test_cappella_expects_hippo.py`, `test_cappella_expects_canon.py`, plus `test_entity_loader_contract.py` and `test_storage_adapter_contract.py`.
- **Platform round-trips**: `test_round_trip.py`, `test_cross_component.py`, `test_hippo_canon.py`, `test_canon_platform.py`, `test_cli_integration.py`, `test_webhook_integration.py`.

**Designed but not built** (your green field, roughly in dependency order):
- Hippo **LinkML-native redesign** — approved, partially landed; sec9 OpenSpec waves still in flight (ext-vocabulary, core-schema, typed-client, generated-rest-surface, provenance-as-linkml-class, id-registry/UUID strategy, computed temporal fields).
- Hippo **PostgreSQL adapter** (multi-user concurrent writes) and **DRS self-URI endpoint** (Bet 3a).
- **Unified ingestion framework**: one `EntityLoader` ABC in Hippo core that *all* loaders (Hippo built-ins, Cappella adapters, CLI ingest) subclass — see `platform/design/sec4_unified_ingestion.md`. Phase 1 in Hippo, phase 3 refactors Cappella onto it.
- Canon v0.2: **storage-adapter plugin system**, dynamic rule registration, convention-based CWL→entity output mapping, Snakemake/Nextflow/Toil executor adapters, FETCH-via-DRS path.
- Cappella v0.2: **concrete external adapters** (STARLIMS, HALO, REDCap — currently absent), webhook + hippo-poll reactive triggers, `SyncRun` audit entity.
- Aperture v0.2: web portal, R/Python client libraries, Canon/Cappella/Bridge integration (v0.1 is Hippo-only).
- **Bridge v0.1**: the entire component — unified `/api/v1/{component}/` routing, API-key auth, `X-Bass-Actor`/`X-Bass-Roles` header injection, flat RBAC, in-process sync event bus.

---

## 5. How to find the next unit of work — the planning pipeline

BASS uses a deterministic pipeline (documented in `CLAUDE.md`):

```
Design spec sections  →  vision.yaml  →  roadmap  →  epics  →  features  →  OpenSpec changes  →  code + tests
```

- **Hippo** is the most mature: `hippo/plan/` + `hippo/openspec/changes/` (many archived/complete, ~15 active). Start from `hippo/design/INDEX.md` (tracks per-section status, key decisions, open questions) and the active OpenSpec changes.
- **Canon**: `canon/plan/openplan/visions/vision.yaml` + `roadmaps/roadmap-canon-v01.yaml` decompose 8 epics; `canon/openspec/changes/` holds active work. The design is *ahead* of code, so most Canon epics are "implement the already-specified thing."
- **Cappella**: `cappella/openplan/` + `cappella/openspec/changes/` (e.g. `adopt-hippo-loaders`).
- **Aperture / Bridge**: design specs exist, but **no planning decomposition yet**. For these you'll author the vision → roadmap → epics first (use the OpenSpec skills available in this environment), then implement.

**The OpenSpec workflow is installed as skills** (`openspec-new-change`, `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change`, etc.). Use them — don't freelance around the pipeline. A change is "done" only when its tasks are implemented, verified, and the relevant test tier is green.

---

## 6. Ambitious targets & milestones

These ladder up to the proposal's **18-month plan**: *(i) bring the PTSD Brain Bank's production metadata into Hippo behind Cappella adapters, (ii) ship open-source v1.0 with reference deployments at 1–2 partner institutions, (iii) drive one biomedical study to publication using BASS as the substrate.* Sequenced by dependency; each milestone has a **Definition of Done** you can verify objectively.

### M1 — Finish the Hippo LinkML core (foundation)
Land the remaining sec9 OpenSpec waves so the schema is fully a runtime artifact end-to-end: ext-vocabulary, hippo_core schema, id-registry/UUID strategy, computed temporal fields, provenance-as-LinkML-class, typed client, generated REST surface.
**DoD:** Adding a new entity type is a pure LinkML edit (no Python change) that flows to tables, SDK types, REST surface, and validation; full hippo test suite green; the three contract suites still pass unchanged.

### M2 — Unified ingestion framework
Implement the single `EntityLoader` ABC in Hippo core, port built-in loaders, then refactor Cappella's adapters to subclass it (`platform/design/sec4_unified_ingestion.md`, phases 1→3). Retire the legacy `hippo.core.ingestion` path.
**DoD:** `tests/contracts/test_entity_loader_contract.py` covers the unified ABC; Cappella adapters import Hippo loaders; no behavioral regression in platform round-trips.

### M3 — Canon to v0.2 (semantic resolution, for real)
Storage-adapter plugin system, dynamic rule registration, convention-based output mapping, and at least one production executor adapter beyond cwltool (Snakemake or Nextflow). Implement the **FETCH-via-DRS** path so REUSE/FETCH/BUILD are all live.
**DoD:** A multi-hop BUILD plan (e.g. FASTQ → AlignmentFile → CountMatrix against a pinned Ensembl release) resolves and executes against the mock executor in platform tests; rule validation coverage measured; cycle detection tested.

### M4 — DRS endpoint + AI-readiness (Bet 3)
Ship Hippo's `drs://host/uuid` GA4GH DRS self-URI endpoint and an MCP (or equivalent) surface that lets an agent traverse derivation chains and resolve artifacts.
**DoD:** An agent can, from a single entity ID and no bespoke code, walk provenance to source artifacts and return a citable, reproducible answer; demonstrated in a platform-level test.

### M5 — Real Brain Bank onboarding (Cappella v0.2)
Concrete adapters for the brain bank's actual source systems (STARLIMS / HALO / REDCap as applicable), reactive triggers (webhook + hippo-poll), and a `SyncRun` audit entity. **This is proposal milestone (i).**
**DoD:** Production brain-bank metadata flows external-source → Cappella → Hippo idempotently; a re-sync of unchanged data is a no-op (provenance proves it); operators can audit every sync.

### M6 — v1.0 deployable stack (proposal milestone ii)
The headline proposal deliverable, verbatim: *"a Docker-Compose deployable stack that lets a new user reproduce a full external-source → harmonization → query → workflow-output round trip from the documentation alone."* Requires Bridge v0.1 (auth gateway + routing), Aperture v0.1 CLI polished, Hippo PostgreSQL adapter, and docs good enough to follow cold.
**DoD:** A fresh user, following only the docs, runs `docker compose up`, ingests a sample source, resolves a workflow output, and queries the result — with no tribal knowledge. Reference deployment stood up at 1–2 partner sites.

### M7 — Publication-grade demonstrator (proposal milestone iii)
Drive one AI-assisted multi-modal cohort analysis to publication using BASS as the substrate. Publish the **synthetic brain-bank metadata benchmark** for the DB + biomedical communities.
**DoD:** A reproducible, BASS-backed study artifact whose value is gated on this infrastructure; benchmark released. (Publication targets the proposal names: VLDB/SIGMOD for the systems threads, Nature Biomedical Engineering / Cell Patterns for the cohort study.)

> **Stretch / aspirational** (don't schedule until M1–M4 are solid): multi-institution federation via Bridge, GraphQL surface, Kubernetes/Helm tier-3 deployment, OAuth 2.0 + hierarchical RBAC, additional storage backends.

---

## 7. Working agreement for autonomous development

**Guardrails — do these without being asked:**
- **Contract-first.** The files in `tests/contracts/` are the load-bearing inter-component API. Treat a contract change as a breaking change: bump the relevant version, update the consumer, and call it out loudly. Never silently weaken a contract to make a test pass.
- **Respect the testing pyramid** (`TESTING.md`): unit (in each component's `tests/`) → contract (`tests/contracts/`) → platform (`tests/platform/`). Before merging anything cross-cutting, run **both** the contract and platform suites with the CI `PYTHONPATH`. They're slow (~7 min contracts, ~6 min platform — LinkML→pydantic codegen) — budget for it; don't skip.
- **Submodule hygiene.** Any hippo change happens in the hippo repo; in drylims it's a *pointer bump in its own PR*, verified against the contract + platform suites. (See §3.)
- **Branch + PR discipline.** Branch off `main`; never commit directly to `main`. One concern per PR. Commit messages reference the issue key (`PTS-NNN`) where one exists. End commit messages with the `Co-Authored-By` trailer.
- **Honor the OpenSpec pipeline** (§5). For components without planning artifacts (Aperture, Bridge), author vision → roadmap → epics *before* coding.
- **Preserve the three bets and SDK-first.** If an implementation shortcut would store state outside Hippo, hard-delete a row, bypass the SDK from a transport layer, or hardcode a schema, it's wrong — find the path that keeps the invariant.

**Conventions (from `CLAUDE.md`):**
- Design specs are numbered, self-contained section files with explicit `Depends on` / `Feeds into` headers; keep that structure when you add sections.
- Hippo's spec is the template for the other components' specs.
- Schemas are authored directly in LinkML; the data model is config-driven relational with a graph-shaped API.

**Escalate to a human (don't decide solo):** anything that publishes or mutates outside the repo (deploys, partner-site coordination, real PHI/brain-bank data handling), the unresolved open design questions in §8, and the "BASS vs DryLIMS" public name. When blocked on one of these, open an issue and keep moving on unblocked work.

---

## 8. Open questions & decisions owed by humans

From the design specs' "Open Questions" sections — surface these, propose options, but don't unilaterally resolve:
1. **Cappella ↔ Hippo write-failure recovery** — persist a retry queue, or rely on operator-configured trigger retries? (High priority; currently the latter.)
2. **Canon routing** — does Cappella call Canon directly (perf) or via Bridge (auth) in multi-server deployments?
3. **Aperture web portal MVP** — feature set for the deferred web tier (SPA vs. server-rendered undecided).
4. **Multi-institution federation** — can Bridge serve as the federation gateway? (v2.0 candidate, needs design.)
5. **Platform name** — "BASS" vs "DryLIMS" before any public announcement.

---

## 9. First moves (your first session)

1. Clone with `git clone --recurse-submodules`; confirm `hippo/` is at the pinned commit.
2. Create a working venv; install components editable as CI does, or set `PYTHONPATH=hippo/src:canon/src:cappella/src:aperture/src`.
3. Run the baseline to confirm the ground truth in §4: `pytest tests/contracts/ -q` then `pytest tests/platform/ -q`. You should see **108 passed** and **114 passed, 1 skipped**. If not, fix the environment before changing anything.
4. Read `hippo/design/INDEX.md` and list the active `hippo/openspec/changes/` — pick the next unblocked sec9 LinkML wave (M1) as your entry point, or, if you want a self-contained win first, take a Canon v0.2 epic (M3) whose spec is already complete.
5. Open an issue for your chosen milestone slice, branch, and go — contract suite green before you call it done.

Welcome aboard. Build the substrate the brain bank — and the agents that will query it — deserve.
