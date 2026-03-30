# Aperture — Interface Layer
## Specification Index

**Codename:** Aperture
**Component:** Interface Layer
**Version:** 0.1 — Draft

---

## Document Map

| File | Section | Status | Notes |
|---|---|---|---|
| `sec1_overview.md` | 1. Overview & Scope | ✅ Draft v0.1 | CLI-first v0.1 scope; personas, design principles, component relationships |
| `sec2_architecture.md` | 2. Architecture | ✅ Draft v0.1 | Typer CLI, backend integration layer (SDK/REST), config, output formatting |
| `sec3_cli.md` | 3. CLI Design | ⬜ Not started | Detailed command UX, interactive flows, completion |
| `sec4_web_ui.md` | 4. Web Interface | ⬜ Not started | Deferred to v0.2 |
| `sec5_api_clients.md` | 5. API Client Libraries | ⬜ Not started | Deferred to v0.2 |
| `sec6_nfr.md` | 6. Non-Functional Requirements | ⬜ Not started | |

---

## Key Decisions Log

| Decision | Choice | Section |
|---|---|---|
| v0.1 delivery scope | CLI-first; web portal and client libraries deferred to v0.2 | sec1 |
| CLI framework | Typer (consistency with Hippo CLI, type-hint driven, auto-completion) | sec2 |
| Backend integration | Protocol-based: `HippoSdkBackend` (local) and `HippoRestBackend` (remote) | sec2 |
| Auth model | Inherit from Bridge; Aperture never implements its own auth | sec1, sec2 |
| v0.1 component integration | Hippo only; Cappella/Canon/Bridge integration deferred to v0.2 | sec1 |
| Output formatting | All commands support `--format table\|json\|csv`; table default for interactive | sec2 |
| Package name | `bass-aperture`; CLI command is `bass` | sec1, sec2 |
| Hippo dependency | Optional via `[local]` install extra; base install uses REST mode only | sec2 |

---

## Open Questions

| Question | Priority | Status |
|---|---|---|
| What is the minimum set of backend integrations Aperture must support at launch? | High | Decided — Hippo only for v0.1 (sec1 §1.5) |
| Does Aperture have its own auth layer or inherit from Bridge? | High | Decided — inherit from Bridge (sec2 §2.8) |
| Is the web interface server-rendered or SPA? | Medium | Deferred to v0.2 |
| Should `bass` namespace conflict with other tools? | Low | Open — may need `bass-cli` or `bassctl` as alternatives |
| Plugin entry point for site-specific CLI commands? | Low | Planned for post-v0.1 (sec2 §2.11) |

---

## How to Use This Spec

Each section document is self-contained and includes `Depends on` and `Feeds into` headers
to make inter-document dependencies explicit. When starting a new section, read the documents
it depends on first.

This spec is designed to feed into the openplan pipeline:
```
Spec sections → openplan vision.yaml → roadmap → epics → features → OpenSpec
```

Each completed section maps to one or more epics in the openplan roadmap.
