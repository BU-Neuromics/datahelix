"""Read the ledger from tags and assemble a queryable ``compatibility.json``.

The tags are the source of truth; ``compatibility.json`` is a CI-assembled
convenience artifact (fast to query, easy to diff, cacheable). It carries both
passing and failing entries — a failing pair is paid-for information.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import _git
from .model import LedgerEntry, TAG_PREFIX


def read_entries(repo: str | Path = ".") -> list[LedgerEntry]:
    """Every ledger entry, parsed from the ``certified/*`` annotated tags.

    Malformed tag messages are skipped with the shape discipline the rest of
    the platform uses (read-and-skip, not crash) — a hand-created junk tag
    under the namespace should not break assembly. Order is stable: by
    timestamp then label.
    """
    entries: list[LedgerEntry] = []
    for tag in _git.list_tags(repo, TAG_PREFIX):
        body = _git.tag_message(repo, tag)
        try:
            entry = LedgerEntry.from_json(body)
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        if entry.validate():
            continue
        entries.append(entry)
    entries.sort(key=lambda e: (e.timestamp, e.label))
    return entries


def assemble(repo: str | Path = ".") -> dict[str, Any]:
    """Build the ``compatibility.json`` document from the ledger tags."""
    entries = read_entries(repo)
    passing = [e for e in entries if e.passed]
    failing = [e for e in entries if not e.passed]
    components: dict[str, set[str]] = {}
    for e in passing:
        for c in e.components:
            components.setdefault(c.name, set()).add(c.version)
    return {
        "schema": "bass.compatibility/v1",
        "generated_from": "certified/* git tags (source of truth)",
        "counts": {
            "total": len(entries),
            "passing": len(passing),
            "failing": len(failing),
        },
        "certified_versions": {
            name: sorted(vers) for name, vers in sorted(components.items())
        },
        "entries": [e.to_dict() for e in entries],
    }


def write_compatibility_json(
    out_path: str | Path, repo: str | Path = "."
) -> dict[str, Any]:
    doc = assemble(repo)
    Path(out_path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return doc
