"""Write a certification result into the ledger.

On a green (or red) certification run, CI calls ``write_entry`` to append one
immutable fact: an annotated ``certified/<label>`` tag whose message is the
entry JSON. This is the *only* way facts enter the ledger.
"""

from __future__ import annotations

from pathlib import Path

from . import _git
from .model import LedgerEntry


def write_entry(
    entry: LedgerEntry,
    *,
    repo: str | Path = ".",
    ref: str = "HEAD",
    push: bool = False,
    remote: str = "origin",
) -> str:
    """Validate ``entry`` and create its annotated ledger tag.

    Returns the tag name. Raises if the entry is invalid or the tag already
    exists (append-only: a pair is certified once and never re-cut).
    """
    entry.raise_if_invalid()
    tag = entry.tag
    _git.create_annotated_tag(repo, tag, entry.to_json(), ref=ref)
    if push:
        _git.push_tag(repo, tag, remote=remote)
    return tag
