---
name: decision-tracker
description: >-
  Track DataHelix platform design and implementation decisions transparently using GitHub
  issues as the deliberation/progress surface, with in-repo ADR files (indexed by each
  component's INDEX Decision Log) as the durable record. Use when the user wants to open a
  decision for discussion, turn an open question / Proposed ADR into a tracked GitHub issue,
  ratify a decision, track implementation progress against a decision, or reconcile issue
  state with the decision record. Covers the datahelix platform repo and the mosaic (hippo),
  aperture, and reel component repos.
---

# Decision Tracker

Drive **GitHub issues** for decision deliberation and progress tracking, while keeping the
**durable decision record in the repo** as **ADR files** (indexed by the component's INDEX
Decision Log). Issues are the front of the pipeline (discussion, labels, links, progress); the
in-repo ADR is the back (versioned, immutable-once-accepted). They cross-link.

> **Model: complement, not replace.** A Proposed decision *is* an open issue; ratifying it
> lands the Accepted ADR in the repo and closes the issue with a link. Never make a GitHub
> issue the sole record of a decision — issues are mutable and external; the record must stay
> versioned in the repo.

## Prerequisites

- GitHub MCP tools (`mcp__github__issue_write`, `issue_read`, `list_issues`,
  `add_issue_comment`, `sub_issue_write`). Load via `ToolSearch` with `select:...` if not
  already available; they may be deferred or briefly disconnected.
- Issue operations are restricted to the session's scoped repos. If the target repo isn't in
  scope, ask the user to add it (`mcp__claude-code-remote__add_repo`) before proceeding.

## Repository map

The platform uses one convention everywhere (platform ADR, `platform/design/decisions/README.md`):
**one ADR file per decision** in the relevant `design/decisions/` directory, indexed by a
Decision Log in that component's `design/INDEX.md`.

| Scope | GitHub owner/name | Submodule mount | Decision record lives in |
|---|---|---|---|
| Platform (DataHelix) | `BU-Neuromics/datahelix` | — (this repo) | cross-component ADRs in `platform/design/decisions/ADR-NNNN-*.md`, indexed by `platform/design/INDEX.md` |
| Mosaic (formerly Hippo, ADR-0004) | `BU-Neuromics/mosaic` | `mosaic/` | ADR files in `design/decisions/` + Key Decisions Log in `design/INDEX.md` — **forward-only**, no mass backfill |
| Aperture | `BU-Neuromics/aperture` | `aperture/` | ADR files in `design/decisions/ADR-NNNN-*.md` + Decision Log in `design/INDEX.md` (the reference implementation) |
| Reel | `BU-Neuromics/reel` | (not mounted) | ADR files in `design/decisions/ADR-NNNN-*.md` + `design/INDEX.md` |

In-tree components (Canon, Cappella, Bridge) live in the DataHelix repo under their own
`<component>/design/decisions/`. Notes:

- The Mosaic **component** was renamed from Hippo (ADR-0004); the repo is now
  `BU-Neuromics/mosaic` and mounts at `mosaic/`.
- Mosaic is a mature component on forward-only ADRs — record *new* decisions as ADRs; don't
  backfill historical ones.

## Label taxonomy

Apply what exists; don't fail if a label is missing (note it in the body instead). Suggested
set (create once in the GitHub UI): `decision`, `status:proposed`, `status:accepted`,
`status:superseded`, `status:rejected`, `task`, `epic`, and a component scope label
(`platform`, `mosaic`, `aperture`, `reel`, `canon`, `cappella`, `bridge`).

---

## Workflow A — Open a decision (Proposed → issue)

When the user wants to start tracking an open question or an existing Proposed ADR:

1. **Ensure the in-repo record exists.** If no ADR file, create one from the repo's
   `design/decisions/_template.md` at the next number, status `Proposed`; add a row to that
   component's INDEX Decision Log.
2. **Create the issue** (`issue_write`): title `ADR-NNNN: <decision title>`; body = **Context**
   + the **question** + the **proposed resolution** (summarize from the ADR, don't duplicate it
   wholesale) + a **link to the ADR file** (GitHub blob URL on the working branch). Labels:
   `decision`, `status:proposed`, component scope.
3. **Cross-link both ways.** Add the issue URL to the ADR (a `Tracking issue:` line in the
   header) and commit. The issue links the file; the file links the issue.

## Workflow B — Ratify a decision (Proposed → Accepted)

When the user ratifies (decides) an open decision:

1. **Update the record.** Flip the ADR `Status: Proposed → Accepted`, set `Date`/`Deciders`,
   fold the session's reasoning into Decision/Alternatives. Update the INDEX Decision Log status.
2. **Commit and push** the record change (respect the repo's working-branch rules).
3. **Close the issue** (`issue_write` state=closed) with a comment (`add_issue_comment`)
   linking the merged record (commit or blob permalink). Swap `status:proposed` →
   `status:accepted` before closing.

## Workflow C — Track implementation progress

For work that implements an Accepted decision:

1. Create **task issues** (`issue_write`, label `task` + scope), each linked to the Accepted
   ADR and, when relevant, to a PR.
2. Group under an **epic** or parent decision using `sub_issue_write` (sub-issues) so progress
   rolls up. The decision issue closes at ratification; *implementation* lives in these task
   issues, not by reopening the decision.
3. Keep PRs linked (`Closes #N`) so merge auto-closes the task and the decision↔code trail is
   visible.

## Workflow D — Supersede

When a new decision reverses an accepted one:

1. New ADR, status `Proposed` → run Workflow A, then B.
2. Mark the old ADR `Superseded by ADR-NNNN` (forward pointer; never delete).
3. On the old issue (if still referenced), add a comment pointing to the superseding issue/ADR.

## Workflow E — Sync / audit

When asked to reconcile:

1. `list_issues` (label `decision`) per repo; read the INDEX Decision Log(s).
2. Report drift: decisions with no issue, issues with no record, status mismatches
   (`status:accepted` label vs. `Proposed` in the file, etc.).
3. Offer to fix each — create missing issues (A), flip stale statuses (B), or annotate.

---

## Style

- The issue is a **pointer + discussion home**, not a second copy of the ADR. Summarize and
  link; let the record hold the canonical detail.
- One decision per issue, mirroring one ADR per decision.
- Be frugal with issue comments — comment on state changes (opened/ratified/superseded), not
  every edit. The ADR's git history is the change log.
- Respect each repo's branch rules. Never push a decision record to a branch without the
  established permission.
