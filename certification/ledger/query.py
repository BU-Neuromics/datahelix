"""Ledger queries — the ones the bump bot and humans actually ask.

The headline query the backport workflow needs: *"which versions of component
B are certified-passing with component A's line X.Y.*?"* — e.g. when hippo cuts
a maintenance release, the bot asks which aperture the LTS line is frozen at.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from .assemble import read_entries
from .model import LedgerEntry


def find_entry(
    label: str, *, repo: str | Path = ".", entries: list[LedgerEntry] | None = None
) -> LedgerEntry | None:
    """The entry whose pair label matches exactly, or None."""
    for e in entries if entries is not None else read_entries(repo):
        if e.label == label:
            return e
    return None


def _matches_line(version: str, line: str) -> bool:
    """``line`` is a glob over versions: ``1.2.*`` matches ``1.2.4``.

    A bare ``X.Y`` is treated as ``X.Y.*`` for convenience.
    """
    pat = line
    if pat.count(".") == 1 and "*" not in pat:
        pat = pat + ".*"
    return fnmatch.fnmatch(version, pat)


def partners_for_line(
    anchor: str,
    line: str,
    partner: str,
    *,
    passing_only: bool = True,
    repo: str | Path = ".",
    entries: list[LedgerEntry] | None = None,
) -> list[str]:
    """Versions of ``partner`` certified alongside ``anchor`` in version ``line``.

    Example — partners of aperture's LTS line 1.4.*, on the hippo side::

        partners_for_line("aperture", "1.4.*", "hippo")
        # -> ["1.2.3", "1.2.4"]   (passing hippo versions seen with aperture 1.4.x)

    Results are de-duplicated and version-sorted.
    """
    seen: set[str] = set()
    for e in entries if entries is not None else read_entries(repo):
        if passing_only and not e.passed:
            continue
        # component_line (not component) so a query for "mosaic" also matches
        # entries recorded under the legacy "hippo" name, and vice versa
        # (decision 1.7 — the two spellings are one component line).
        a = e.component_line(anchor)
        p = e.component_line(partner)
        if a is None or p is None:
            continue
        if _matches_line(a.version, line):
            seen.add(p.version)
    return sorted(seen)
