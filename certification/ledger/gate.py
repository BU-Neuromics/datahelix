"""Deploy-side gate — the enforcement point that makes independent shipping safe.

Whatever installs a composition must call this *before* proceeding. It refuses
any component pair not present as a passing ledger entry, and — critically —
verifies the *digests* match, so a rebuilt artifact under a certified version
number is rejected (ADR-0001 immutability rule).
"""

from __future__ import annotations

from pathlib import Path

from .assemble import read_entries
from .model import Component, LedgerEntry


class GateError(RuntimeError):
    """Raised when a requested composition is not certified for deployment."""


def _find_pair(
    requested: list[Component], entries: list[LedgerEntry]
) -> LedgerEntry | None:
    for e in entries:
        if len(e.components) != len(requested):
            continue
        # component_line (not exact name match) so a request for "mosaic"
        # is satisfied by an entry recorded under the legacy "hippo" name,
        # and vice versa (decision 1.7 — one component line, two spellings).
        matches = True
        for want in requested:
            got = e.component_line(want.name)
            if got is None or got.version != want.version:
                matches = False
                break
        if matches:
            return e
    return None


def is_certified(
    requested: list[Component],
    *,
    repo: str | Path = ".",
    entries: list[LedgerEntry] | None = None,
) -> bool:
    """True iff ``requested`` (versions AND digests) is a passing ledger entry."""
    try:
        check_pair(requested, repo=repo, entries=entries)
        return True
    except GateError:
        return False


def check_pair(
    requested: list[Component],
    *,
    repo: str | Path = ".",
    entries: list[LedgerEntry] | None = None,
) -> LedgerEntry:
    """Return the passing entry for ``requested`` or raise ``GateError``.

    The message names exactly why the gate refused so deploy tooling can print
    something actionable (uncertified → run a backfill; digest mismatch →
    someone re-cut a release).
    """
    ledger = entries if entries is not None else read_entries(repo)
    entry = _find_pair(requested, ledger)
    if entry is None:
        want = ", ".join(f"{c.name} {c.version}" for c in requested)
        raise GateError(
            f"no ledger entry certifies the pair ({want}). This composition is "
            "uncertified — run an on-demand backfill (workflow_dispatch) to "
            "certify it before deploying (ADR-0001)."
        )
    if not entry.passed:
        raise GateError(
            f"pair {entry.label} is certified FAILING "
            f"(failing check: {entry.failing_check}); refusing to deploy."
        )
    # Version match confirmed; now enforce digests (alias-aware lookup).
    mismatches = [
        f"{c.name}: requested {c.digest} but ledger certified "
        f"{entry.component_line(c.name).digest}"
        for c in requested
        if entry.component_line(c.name).digest != c.digest
    ]
    if mismatches:
        raise GateError(
            "digest mismatch — a certified version number was re-cut with a "
            "different artifact (forbidden by ADR-0001 immutability):\n  - "
            + "\n  - ".join(mismatches)
        )
    return entry
