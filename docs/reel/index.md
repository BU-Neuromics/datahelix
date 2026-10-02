# Reel — AI-Native Data-Story Engine

!!! info "Mounted as a submodule"
    Reel lives in its own repo, [BU-Neuromics/reel](https://github.com/BU-Neuromics/reel),
    and is wired into this monorepo as a git submodule. It was split from Aperture per
    [platform ADR-0003](https://github.com/BU-Neuromics/datahelix/blob/main/platform/design/decisions/ADR-0003-reel-data-story-engine-separate-from-portal.md) so the portal could
    ship without waiting on the story engine.

Reel is the **data-story engine**: the headless interaction core that composes query states into
replayable, reproducible stories. A story is an **instruction path** — `state[n] =
apply(instruction[n], state[n-1])` — over a typed op catalog, deterministic and pinned to an
as-of watermark, so a result can be re-derived rather than merely re-described.

Reel **composes the query noun; it does not define one.** Its v1 `State` *is* the platform
`QuerySpec` — the same artifact Aperture builds in its query builder and Mosaic validates and
executes at its MCP boundary (Reel ADR-0006). A change to that noun goes to its owner first.
Reel adds sequencing, forking, watermark pinning per story-version, and set-ops between states.

Reel produces **View Contract instances** — serializable descriptions plus the data to render
them — never pixels. A thin, replaceable shell realizes them; the Aperture portal is *a* shell,
the reference renderer, not the product (Reel ADR-0005).

## Status

Reel had no code from the 2026-06-22 split until **Phase B-runtime** of the Exon migration
carried the turn path across from the prototype it was seeded by. What exists today:

| | |
|---|---|
| `src/reel/story/` | the turn contract and conversation model — v1 wire form of `Instruction` |
| `src/reel/planner/` | the schema-grounded `QuerySpec` emitter and its capability grounding |
| `src/reel/serve/` | the conversational turn endpoint Mosaic's relay calls |
| `src/reel/evals/` | discovery evals and grading |

**Not yet carried:** the reliability harness (`exon/harness/` — probe, runner, grading, refine
loop), which is gated on retiring the prototype's `QueryPlan` path so the harness's own
before/after is not lost mid-refactor. See
[`proposals/exon-migration.md`](https://github.com/BU-Neuromics/reel/blob/main/proposals/exon-migration.md)
for the runbook and its preconditions.

Reel is **not yet in the certified-frontier ledger** (platform ADR-0001) — that waits on a
release and a Mosaic pair to certify against.

## Where its decisions live

The [Decision Log](https://github.com/BU-Neuromics/reel/blob/main/design/INDEX.md) is the index
of record. Load-bearing ones: ADR-0001 (the instruction-path model), ADR-0003 (grain discipline
— arbitrary joins rejected), ADR-0005 (headless core, thin shell), ADR-0006 (v1 `State` is the
`QuerySpec`), ADR-0007 (validation and execution delegated to Mosaic's boundary), ADR-0008
(Exon seeds Reel).
