# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

This is the **platform integration repository** for the **BASS (Bioinformatics Analysis Software System)** platform. It hosts cross-cutting platform docs, the unified mkdocs site, and cross-component integration tests under `tests/platform/` and `tests/contracts/`. Component source code lives in component directories — some in-tree, some as git submodules pointing at standalone component repos.

## Repository Layout

```
<component>/
├── design/     # Engineering specification (internal, structured sections)
│   └── INDEX.md
├── docs/       # User-facing documentation
└── src/        # Component source (in-tree) — or this dir IS a submodule (hippo)
platform/       # Cross-cutting platform docs (architecture, glossary, deployment)
tests/
├── contracts/  # Consumer-expectation contract tests (e.g. test_canon_expects_hippo.py)
└── platform/   # Cross-component integration tests (real Hippo + Canon in-process)
```

**Components:** Hippo (metadata tracking — submodule at [BU-Neuromics/hippo](https://github.com/BU-Neuromics/hippo)), Cappella (workflow engine), Aperture (interface layer / config-driven data portal — submodule at [BU-Neuromics/aperture](https://github.com/BU-Neuromics/aperture)), Bridge (integration middleware). Hippo was split out 2026-05-25 (see `proposals/hippo-split.md`); Aperture was split out 2026-06-13 as a fresh start carrying only the Hippo backend protocol + portal design (see `proposals/aperture-split.md`). The remaining in-tree components are expected to follow the same pattern.

**Working with submodules:** Clone with `git clone --recurse-submodules`. To bump a submodule's pinned version: `git submodule update --remote <hippo|aperture>`, verify, then commit the submodule pointer change.

## Key Conventions

- Each component's design spec is split into numbered section files (`sec1_overview.md`, `sec2_architecture.md`, etc.) with explicit `Depends on` / `Feeds into` headers for cross-referencing.
- The Hippo `design/INDEX.md` tracks section status (complete, in review, not started), key decisions, and open questions. Other components follow the same pattern.
- Design specs feed into the **openplan** pipeline: `Spec sections → vision.yaml → roadmap → epics → features → OpenSpec`.
- The `.gitignore` excludes `.obsidian/` (Obsidian editor config).

## Writing Guidelines

- Design spec sections should be self-contained and reference dependencies on other sections explicitly.
- Hippo is the most developed component; use its spec structure as the template when drafting specs for other components.
- The platform uses an **SDK-first** architecture — business logic in Python SDK, REST/GraphQL as thin transport wrappers. Keep this principle consistent across all component docs.
- Hippo's data model uses a **config-driven relational** approach with a graph-shaped API and schemas authored directly in LinkML.
