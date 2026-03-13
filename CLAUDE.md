# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

This is a **documentation-only** repository for the **BASS (Bioinformatics Analysis Software System)** platform. There is no application code, build system, or test suite — only Markdown design specs and user-facing docs.

## Repository Layout

```
<component>/
├── design/     # Engineering specification (internal, structured sections)
│   └── INDEX.md
└── docs/       # User-facing documentation
platform/       # Cross-cutting platform docs (architecture, glossary, deployment)
```

**Components:** Hippo (metadata tracking), Cappella (workflow engine), Aperture (interface layer), Bridge (integration middleware).

## Key Conventions

- Each component's design spec is split into numbered section files (`sec1_overview.md`, `sec2_architecture.md`, etc.) with explicit `Depends on` / `Feeds into` headers for cross-referencing.
- The Hippo `design/INDEX.md` tracks section status (complete, in review, not started), key decisions, and open questions. Other components follow the same pattern.
- Design specs feed into the **openplan** pipeline: `Spec sections → vision.yaml → roadmap → epics → features → OpenSpec`.
- The `.gitignore` excludes `.obsidian/` (Obsidian editor config).

## Writing Guidelines

- Design spec sections should be self-contained and reference dependencies on other sections explicitly.
- Hippo is the most developed component; use its spec structure as the template when drafting specs for other components.
- The platform uses an **SDK-first** architecture — business logic in Python SDK, REST/GraphQL as thin transport wrappers. Keep this principle consistent across all component docs.
- Hippo's data model uses a **config-driven relational** approach with a graph-shaped API and a Hippo DSL (YAML/JSON) compiled to LinkML.
