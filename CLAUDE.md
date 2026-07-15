# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

This is the **platform integration repository** for the **DataHelix** platform. It hosts cross-cutting platform docs, the unified mkdocs site, and cross-component integration tests under `tests/platform/` and `tests/contracts/`. Component source code lives in component directories — some in-tree, some as git submodules pointing at standalone component repos.

## Repository Layout

```
<component>/
├── design/     # Engineering specification (internal, structured sections)
│   └── INDEX.md
├── docs/       # User-facing documentation
└── src/        # Component source (in-tree) — or this dir IS a submodule (mosaic)
platform/       # Cross-cutting platform docs (architecture, glossary, deployment)
tests/
├── contracts/  # Consumer-expectation contract tests (e.g. test_canon_expects_mosaic.py)
└── platform/   # Cross-component integration tests (real Mosaic + Canon in-process)
```

**Components:** Mosaic (formerly Hippo, ADR-0004; LinkML runtime — the platform's structured domain graph; metadata tracking is one application — submodule at [BU-Neuromics/mosaic](https://github.com/BU-Neuromics/mosaic)), Cappella (workflow engine), Aperture (interface layer — AI-native data & workflow explorer; the config-driven portal is its substrate — submodule at [BU-Neuromics/aperture](https://github.com/BU-Neuromics/aperture)), Bridge (integration middleware / auth gateway — the platform's sole PEP/PDP). Hippo was split out 2026-05-25 (see `proposals/hippo-split.md`); Aperture was split out 2026-06-13 as a fresh start carrying only the Hippo backend protocol + portal design (see `proposals/aperture-split.md`). The remaining in-tree components are expected to follow the same pattern.

**Working with submodules:** Clone with `git clone --recurse-submodules`. To bump a submodule's pinned version: `git submodule update --remote <mosaic|aperture>`, verify, then commit the submodule pointer change.

## Key Conventions

- Each component's design spec is split into numbered section files (`sec1_overview.md`, `sec2_architecture.md`, etc.) with explicit `Depends on` / `Feeds into` headers for cross-referencing.
- The Mosaic `design/INDEX.md` tracks section status (complete, in review, not started), key decisions, and open questions. Other components follow the same pattern.
- **Design decisions are recorded as ADRs** (Architecture Decision Records), one file per decision in each component's `design/decisions/`, following the platform-wide convention in [`platform/design/decisions/README.md`](platform/design/decisions/README.md). Each component's `design/INDEX.md` Decision Log indexes its ADRs; platform-wide (cross-component) decisions live in `platform/design/decisions/`. New/non-trivial decisions get an ADR; mature components (Mosaic) adopt forward-only (no mass backfill). Aperture's `design/decisions/` is the reference implementation.
- Design specs feed into the **openplan** pipeline: `Spec sections → vision.yaml → roadmap → epics → features → OpenSpec`.
- The `.gitignore` excludes `.obsidian/` (Obsidian editor config).

## Writing Guidelines

- Design spec sections should be self-contained and reference dependencies on other sections explicitly.
- Mosaic is the most developed component; use its spec structure as the template when drafting specs for other components.
- The platform uses an **SDK-first** architecture — business logic in Python SDK, REST/GraphQL as thin transport wrappers. Keep this principle consistent across all component docs.
- Mosaic's data model uses a **config-driven relational** approach with a graph-shaped API and schemas authored directly in LinkML.
