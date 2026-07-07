# DataHelix Platform — Design Decisions (ADRs)

This is the **canonical decision-recording convention for the DataHelix platform** and every
component in it. Each component records its load-bearing design decisions as **ADRs**
(Architecture Decision Records) in its own `design/decisions/` directory, following the format
and lifecycle defined here. Platform-wide (cross-component) decisions live in *this* directory.

> If a decision isn't recorded as an ADR, it isn't decided. Prose in a vision/handoff doc is
> *context*; an ADR is the *decision*.

## The system, in one paragraph

Each decision is an **ADR**: a numbered Markdown file (`ADR-NNNN-slug.md`) with a status, the
context that forced the choice, the decision itself, its consequences, and the alternatives
rejected. Each component's `design/INDEX.md` carries a **Decision Log** table — one row per ADR,
status-tracked — which is the scannable index of record. Open questions are ADRs in `Proposed`
status (the *decision queue*); ratifying one is a status flip from `Proposed` → `Accepted`, not
a new document.

## Lifecycle and statuses

```
        ┌─────────┐  ratify   ┌──────────┐  revisit   ┌─────────────┐
new ───►│ Proposed│ ────────► │ Accepted │ ─────────► │ Superseded  │
        └─────────┘           └──────────┘            │ by ADR-NNNN │
             │                                         └─────────────┘
             └────────► Rejected (kept, not deleted)
```

| Status | Meaning |
|---|---|
| `Proposed` | An open question with a recommended resolution. In the decision queue; not yet binding. |
| `Accepted` | Ratified. Binding on the component's source and design. Change only by superseding. |
| `Rejected` | Considered and declined. Kept for the record (never deleted) so we don't relitigate. |
| `Superseded by ADR-NNNN` | Was `Accepted`, now replaced. Points forward to its replacement. |

**Decisions are never deleted.** A reversed decision is `Superseded`, with a forward pointer.

## How a decision gets made

1. **Raise it as a `Proposed` ADR.** Copy [`_template.md`](./_template.md), take the next number
   for that component, fill in Context + the question, and record the recommended resolution
   under Decision. Add the row to the component's INDEX Decision Log with status `Proposed`.
2. **Pressure-test it.** Capture alternatives weighed and any probe results in the ADR.
3. **Ratify.** When agreed, flip the status to `Accepted`, set the date, and update the INDEX
   row. If it replaces an earlier decision, mark the old one `Superseded by` this one.

## Where ADRs live

- **Component-specific decisions** → `<component>/design/decisions/` (e.g.
  `aperture/design/decisions/`, `hippo/design/decisions/`). Numbering is per-component.
- **Platform-wide / cross-component decisions** → `platform/design/decisions/` (this directory).
- Each component keeps the canonical process *here* and may keep a local
  `decisions/README.md` (a short pointer back to this doc) and a local copy of `_template.md`
  for convenience.

## Adoption (hybrid for mature components)

Components with a large body of already-settled, shipped decisions adopt ADRs **forward-only**:
new, non-trivial, or still-in-flux decisions get an ADR; an existing decisions log (e.g. Hippo's
**Key Decisions Log** in `hippo/design/INDEX.md`) remains the scannable index and is backfilled
only **opportunistically** (when a settled decision is revisited and its alternatives are worth
capturing) — never as a mass migration. Components designed ADR-first (Aperture) record
essentially all load-bearing decisions as ADRs.

## Conventions

- **Numbering:** zero-padded, monotonic per component, never reused. Gaps are fine; numbers are
  stable IDs.
- **Slugs:** short, decision-shaped (`ADR-0011-component-execution-runtime.md`).
- **One decision per ADR.** If you're writing "and also," it's two ADRs.
- **Cross-component dependencies link both ways.** When a component's ADR imposes a requirement on
  another component, reference the other component's ADR / spec section so the dependency is
  legible from both sides.
- **Supersede, don't edit history.** Correcting a typo is fine; reversing a decision means a new
  ADR that supersedes the old one.

## Reference implementation

[`aperture/design/decisions/`](../../../aperture/design/decisions/) is the reference
implementation of this convention.
