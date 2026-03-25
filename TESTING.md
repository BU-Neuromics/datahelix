# TESTING.md — BASS Platform Test Strategy

## Overview

The BASS platform uses a three-tier testing model. Each tier has a distinct purpose and failure protocol.

```
┌──────────────────────────────────────────────────────────────────┐
│  Tier 3: Platform Tests   tests/platform/                        │
│  "Do components work correctly together?"                        │
│  Real Hippo + Canon in-process, mocked CWL executor             │
│  Run after tiers 1 & 2 both pass                                 │
├──────────────────────────────────────────────────────────────────┤
│  Tier 2: Contract Tests   tests/contracts/                       │
│  "Does each component fulfill its published behavioral spec?"    │
│  Component tested in isolation against explicit behavior claims  │
│  Run after tier 1 passes                                         │
├──────────────────────────────────────────────────────────────────┤
│  Tier 1: Unit Tests       hippo/tests/  canon/tests/             │
│  "Does this component work correctly in isolation?"              │
│  Mocked dependencies, fast, run on every commit                  │
└──────────────────────────────────────────────────────────────────┘
```

## Tier 1 — Unit Tests

**Location:** `hippo/tests/`, `canon/tests/`

**What they cover:** Internal logic, edge cases, error paths. Dependencies are mocked.

**Run:**
```bash
cd hippo && uv run pytest tests/ -v
cd canon && uv run pytest tests/ -v
```

**When they fail:** Fix the component directly. Do not look at tier 2/3.

---

## Tier 2 — Contract Tests

**Location:** `tests/contracts/`

**What they cover:** Explicit behavioral specifications for each component's *public interface*, written from the perspective of its consumers. This is the formal answer to "what does Canon need Hippo to do?"

Contract tests differ from unit tests in that they:
- Are written from the *consumer's perspective*, not the provider's
- Assert behavioral guarantees that must not change without a version bump
- Catch API drift early — before a full platform run is needed

Each contract file is named `test_<consumer>_expects_<provider>.py` and contains only assertions about the provider's public interface.

**Current contracts:**
- `test_canon_expects_hippo.py` — behaviors Canon depends on from HippoClient
- `test_hippo_self_contract.py` — Hippo's own behavioral invariants (entity CRUD, validation, provenance)

**Run:**
```bash
PYTHONPATH=hippo/src:canon/src uv run pytest tests/contracts/ -v
```

**When they fail:**
1. If the failure is in `test_<consumer>_expects_<provider>`: the *provider* changed its behavior in a breaking way. Add a unit test to the provider pinning the correct behavior, then fix it.
2. If the failure is in `test_<provider>_self_contract`: the provider violated one of its own invariants. Same protocol.
3. Update the contract spec if the change was intentional (semver bump).

### Writing New Contracts

When you add a new cross-component dependency, add a contract immediately:

```python
# tests/contracts/test_canon_expects_hippo.py
class TestHippoQueryContract:
    """Canon depends on HippoClient.query() behaving exactly like this."""

    def test_query_returns_paginated_result_with_items(self, hippo_client):
        """Canon iterates result.items — must be a PaginatedResult."""
        ...
```

A failing contract test is a **breaking change signal**. Treat it like a failed type check.

---

## Tier 3 — Platform Tests

**Location:** `tests/platform/`

**What they cover:** End-to-end scenarios using real in-process components. Canon talks to a real HippoClient via `HippoClientShim` (no HTTP server). CWL execution is mocked.

**Run:**
```bash
PYTHONPATH=hippo/src:canon/src uv run pytest tests/platform/ -v
```

**Test files:**
- `test_hippo_platform.py` — Hippo-only: CRUD, CEL validation, FTS5, REST API, supersession, external IDs
- `test_canon_platform.py` — Canon-only: rules DSL, entity ref parsing, planner decisions, sidecar, ingestion
- `test_hippo_canon.py` — Cross-cutting: Canon resolving against real Hippo, full bioinformatics chain, idempotency

**When they fail:**
1. Identify which component's behavior changed
2. Check if its unit tests still pass — if not, fix unit tests first
3. Check if the relevant contract test fails — if so, follow the contract failure protocol
4. If unit + contract pass but platform fails, it's an integration issue — add a targeted platform test for the specific interaction, then fix

> **Policy: Contract/platform failures MUST be addressed via TDD.** See [TDD Policy](#tdd-policy) below.

**Markers:**
- `@pytest.mark.platform` — all platform tests
- `@pytest.mark.xfail` — known API gaps, with documented reason and revisit note

---

## Full Test Run

```bash
make test
```

This runs all three tiers in order, failing fast at each stage.

---

## Contract Specification: Component Interfaces

### HippoClient — Canon's View

These are the behaviors Canon depends on. Any change to these is a breaking change for Canon.

| Method | Behavioral guarantee |
|--------|---------------------|
| `query(entity_type)` | Returns a `PaginatedResult` with `.items` (list of dicts). Each item has `id`, `entity_type`, `data` keys. |
| `query(entity_type, limit=N)` | Returns at most N items. |
| `create(entity_type, data)` | Returns a dict with `id` (str UUID), `entity_type`, `data`, `version` (int, starts at 1), `created_at`, `updated_at`. |
| `create()` with missing required field | Raises `ValidationFailure`. |
| `get(entity_type, id)` | Returns same shape as `create()`. Raises `EntityNotFoundError` if not found **or if entity is deleted/superseded** (unless `include_unavailable=True`). |
| `get(entity_type, id, include_unavailable=True)` | Returns entity regardless of deleted/superseded status. Use for audit/provenance queries only. |
| `update(entity_type, id, data)` | Updates entity, returns new version. Raises `EntityNotFoundError` if id does not exist. |
| `supersede_entity(old_id, new_id)` | Marks old entity as superseded. Old entity excluded from `query()` and raises on `get()` by default. |
| `delete(entity_type, id)` | Returns `True`. Entity excluded from `query()` results and raises on `get()` by default. |

**Gaps being addressed via TDD (currently xfail):**
- `get()` availability filtering — in progress, see `hippo/tests/core/test_client_availability.py`
- `update()` existence check — in progress, same file

### HippoQueryClient — Canon's HTTP shim

Canon's `HippoQueryClient` wraps the HTTP API. The `HippoClientShim` in `tests/platform/conftest.py` is the in-process equivalent. When the HTTP API changes, update both.

---

## TDD Policy

**When a contract or platform test fails (or is marked `xfail`), the fix MUST follow this TDD sequence:**

```
1. RED   — Write unit tests in the affected component (hippo/tests/ or canon/tests/)
            that assert the desired behavior. Run make test — new tests fail,
            everything else passes.

2. GREEN — Implement the minimum code change to make the unit tests pass.
            Run make test — all unit tests pass.

3. REFACTOR — Remove xfail markers from the contract/platform tests that
               triggered this cycle. Run make test — those tests now pass as
               hard assertions. 0 failures, 0 unexpected xfails.
```

**Why this matters:**
- Contract/platform tests describe *what* we want but at too high a level to drive implementation safely
- Writing unit tests first forces the API design (method signatures, error types, flag names) to be explicit before touching production code
- The red→green signal is unambiguous — you know exactly when the implementation is correct
- You end up with regression coverage at the right layer (component unit tests), not just at the integration level

**When NOT to use TDD:**
- Trivial one-liner fixes where the behavior is already pinned by existing unit tests
- Documentation or comment updates
- Test-only changes (adding more test cases to an existing passing test)

**The test to add lives in the component whose code changes.** If Hippo's `client.py` changes, add tests to `hippo/tests/`. If Canon's `planner.py` changes, add tests to `canon/tests/`. Contract and platform tests are the early warning system; unit tests are where the fix is pinned.

---

## Failure Protocol Summary

```
Platform test fails
    │
    ├─► Is the failing assertion about a single component's behavior?
    │       └─► YES → go to that component's unit tests
    │                   ├─► Unit test also fails → fix component, add unit test
    │                   └─► Unit test passes → add a contract test, then fix
    │
    └─► Is it a cross-component interaction issue?
            └─► YES → add a targeted platform test, fix the integration
```

When a platform test reveals a behavioral gap (something that *should* work but doesn't):
1. Mark it `@pytest.mark.xfail(reason="...", strict=False)` with a clear reason
2. File it as a backlog item in the relevant component's plan
3. Remove the `xfail` when the feature is implemented

---

## Running Individual Tiers

```bash
# Tier 1 only
cd hippo && uv run pytest tests/ -v
cd canon && uv run pytest tests/ -v

# Tier 2 only
PYTHONPATH=hippo/src:canon/src uv run pytest tests/contracts/ -v

# Tier 3 only
PYTHONPATH=hippo/src:canon/src uv run pytest tests/platform/ -v

# All tiers
make test

# Just the cross-cutting platform tests
PYTHONPATH=hippo/src:canon/src uv run pytest tests/platform/test_hippo_canon.py -v

# Only xfail tests (to check if gaps have been closed)
PYTHONPATH=hippo/src:canon/src uv run pytest tests/platform/ -v -m "xfail"
```
