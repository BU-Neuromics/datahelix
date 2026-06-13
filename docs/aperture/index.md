# Aperture — Config-Driven Data Portal

!!! info "Now a standalone repository"
    Aperture lives in its own repo, [BU-Neuromics/aperture](https://github.com/BU-Neuromics/aperture),
    and is wired into this monorepo as a git submodule. The earlier CLI-first v0.1 design
    and implementation were superseded by the portal vision and remain only in `drylims`
    history.

Aperture is the **interface layer** of the BASS platform: a **config-driven data portal**
that talks to [Hippo](../hippo/index.md) (the LinkML runtime + GraphQL/REST data store).
Browsing, faceted search, view construction/export, and visualization are **configured,
not coded**, for the common cases; custom behavior is delivered through typed, sandboxed
plugins/components rather than a scripting layer.

Aperture does not contain business logic. It is generic against *any* Hippo deployment +
LinkML schema — the brain-bank portal is simply the first and most-tested instance.

## Guiding Intent

A non-technical user should be able to point a coding agent (e.g. Claude Code) at their
Aperture instance — local or an authenticated endpoint — and ask it to add or modify
functionality. The agent edits **config** (always safe, unsupervised) and can scaffold
**components** (which run sandboxed and are validated before going live).

## Settled Architectural Decisions

| Decision | Choice |
|---|---|
| **Generic, not domain-specific** | No brain-bank domain nouns in source; those live only in schema + config |
| **Config is LinkML, stored in Hippo** | Validation, versioning, provenance, and GraphQL/REST access for free — no bespoke persistence |
| **Three levels of configurability** | Composition + Binding are declarative; Behavior is typed sandboxed plugins only (no middle scripting layer) |
| **Components hold no authority** | Data reach resolved against the current viewer via an injected capability-scoped client |
| **Components emit view descriptions** | Serializable view specs, never direct DOM manipulation — enables headless validation |

See the [Portal Vision handoff](design/portal-vision-handoff.md) for the authoritative
problem statement and full decision list.

## What Exists Today

The standalone repo currently ships the reusable Hippo backend foundation that the portal
is built on:

- **`HippoBackend` protocol** with two adapters — `HippoSdkBackend` (in-process SDK) and
  `HippoRestBackend` (REST API) — selected via `create_backend(config)`.
- **`ApertureConfig`** — resolves Hippo backend settings from config files and `BASS_*`
  environment variables.

The portal application (config-in-Hippo, the agent-driven dev loop, the typed component
contract, and the visualization catalog) is built on top of this foundation.

## Related Components

- [Hippo](../hippo/index.md) — the LinkML data + config store Aperture renders over
- [Cappella](../cappella/index.md) — workflow engine (later integration)
- [Canon](../canon/index.md) — artifact resolution (later integration)
- [Bridge](../bridge/index.md) — authentication delegation for multi-user deployments

## Design Documentation

- [Design Index](design/INDEX.md)
- [Portal Vision (Handoff)](design/portal-vision-handoff.md) — authoritative vision and settled decisions
- [Open Questions](design/portal-open-questions.md) — proposed resolutions to the load-bearing open questions
