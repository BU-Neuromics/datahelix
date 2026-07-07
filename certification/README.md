# Composition certification & the certified-frontier ledger

This directory implements the cross-component **version-compatibility strategy**
for the DataHelix platform. Components (aperture, hippo) version and ship
independently; drylims certifies that **one exact version pair at a time** boots
and passes the golden-path scenarios, and records each result in an append-only
**ledger**. Deployment is gated on that ledger.

**The decision of record is [platform ADR-0001](../platform/design/decisions/ADR-0001-certified-frontier-composition.md).**
This README is the runbook.

## The one-paragraph model

Never test the version matrix — walk a single path through it. Each green
certification of the current pins appends one immutable fact
*(aperture X @ digest, hippo Y @ digest, suite S @ sha → pass)* to the ledger.
Facts are about immutable artifacts, so they never expire and are never
re-tested. Deploy tooling refuses any pair not present as a passing ledger
entry. Matrix holes are fine: an off-path pair a deployment needs is filled by a
lazy, targeted **backfill** (`workflow_dispatch`), never a standing matrix.

## Layout

| Path | What it is |
|---|---|
| `composition.lock.json` | The current pins for this branch's line (versions + digests + fixture). The bump bot moves one component per PR; certification reads this. |
| `ledger/` | The ledger tooling (`bass-ledger`): `certify`, `assemble`, `query`, `gate`. Pure stdlib + git. |
| `fixtures/bootstrap/` | Versioned seed schema + data + the Aperture control-plane recipe. One source, consumed by drylims CI **and** (later) hippo CI for the aperture contract file. |
| `compose/` | `docker-compose.certify.yml` + `hippo.certify.yaml` — boots the pinned pair (hippo serve --graphql over the fixture + the aperture SPA). |
| `scenarios/` | The golden-path Playwright suite — **one scenario per product loop**, under a hard ~10-min budget. |
| `scripts/` | `read_lock.py` (resolve pins), `run_composition.sh` (boot + seed + run under budget), `deploy_gate.sh` (deploy pre-flight). |
| `compatibility.json` | CI-assembled view of the ledger tags, for easy querying. Tags are the source of truth. |

## The three test layers (where this sits)

| Layer | Runs in | Proves |
|---|---|---|
| Component CI | each component repo | the component works in isolation |
| **Contract checks** | the **producer's** CI (aperture's contract file booted against `hippo serve` in hippo's PR CI) | the seam shapes hold, at authorship time |
| **Composition certification** | here, on bump PRs | one exact pair boots and passes the golden path |

The four seams the golden path exercises (isolated in aperture `web/src/data/`):
introspection enrichment, filter SDL, the `batchPut` batch unit-of-work
(Aperture ADR-0028 ↔ Hippo #84), and the control-plane document type (Aperture
ADR-0032). The aperture contract file (aperture#16) does not exist yet — **until
it does, this suite is the only seam check.**

## Golden-path scenarios (one per product loop)

| Loop | Scenario | Seam |
|---|---|---|
| Browse / filter | `scenarios/tests/browse-filter.spec.ts` | introspection + filter SDL |
| Single-entity write | `scenarios/tests/single-entity-write.spec.ts` | create mutation |
| Atomic multi-entity workflow | `scenarios/tests/atomic-workflow.spec.ts` | batch unit-of-work |
| Control-plane saved views / drafts | `scenarios/tests/control-plane.spec.ts` | control-plane document type |

Budget is enforced twice: `playwright.config.ts` (`globalTimeout`) and
`run_composition.sh` (`BUDGET_SECONDS`, which also covers artifact pull + boot +
seed). A new scenario that would blow the budget must merge with or replace
another, or move to the non-blocking nightly tier.

## The frontier flow

1. A component releases → the **bump bot** ([`../renovate.json`](../renovate.json))
   opens one drylims PR moving that one pin. One release = one delta.
2. The certification workflow ([`../.github/workflows/certify.yml`](../.github/workflows/certify.yml))
   reads the lock, pulls both artifacts by digest, boots the composition, runs
   the suite under budget.
3. **Green:** merge. **Patch bumps auto-merge on green**; minor/major need
   review. On the merge (push) the workflow appends the ledger tag and refreshes
   `compatibility.json`.
4. **Red:** the PR is a cross-team pager, not backlog. The ledger records the
   failing pair. On the frontier the consumer adapts (aperture ships a compatible
   version); the bot then bumps both pins and certifies the new pair.

## Maintenance lines & backports

Supported set = **latest + at most one LTS line**. A maintenance line freezes
both its code and its contracts: its drylims branch (`release/lts-*`) carries its
own `composition.lock.json` and pins the era-appropriate fixture version. If a
backport certification fails against the line's frozen partners, **the backport
is wrong** — revise it, never upgrade the pinned consumer. See ADR-0001 §4 and
the failure-asymmetry rule.

## Common commands

```bash
# ledger tooling tests (runnable anywhere)
make ledger-test

# which hippos are certified with aperture's LTS line 1.4.*?
make ledger-query ANCHOR=aperture LINE='1.4.*' PARTNER=hippo

# rebuild compatibility.json from the tags
make ledger-assemble

# deploy pre-flight — refuse an uncertified pair
make deploy-gate

# boot the pinned pair + run the golden path locally (needs published images)
HIPPO_IMAGE=ghcr.io/bu-neuromics/hippo@sha256:... \
APERTURE_IMAGE=ghcr.io/bu-neuromics/aperture@sha256:... \
  make certify-local

# on-demand backfill of an off-path pair (CI): run the "Certify composition"
# workflow via workflow_dispatch with the two versions + digests.
```

## Current status (2026-07)

The tooling, fixtures, compose, scenarios, workflow, and gate are in place. The
components do **not** yet publish digest-addressed artifacts (hippo has no
release/image pipeline; aperture has no Dockerfile, and its live-`hippo serve`
GraphQL integration and consumer contract file are unstarted, aperture#15/#16).
Note the direction of the seam: **Hippo is the GraphQL provider** (`hippo serve
--graphql`); **Aperture is the client/consumer** — its SPA queries Hippo's
autogenerated transport and the contract file is the consumer's assertions about
that transport (run in Hippo's CI). Until these land:

- `composition.lock.json` digests are `null` and the certification workflow
  **skips the boot as an honest no-op** — it never certifies an unpublished pair.
- The ledger starts empty; `compatibility.json` reflects that.
- The ledger tooling and its tests run today (`make ledger-test`).

The component-side prerequisites are tracked in those repos (see ADR-0001
Consequences). This infrastructure was built first, deliberately — it does not
wait on them.
