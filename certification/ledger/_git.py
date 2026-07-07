"""Thin git-over-subprocess helpers for reading/writing ledger tags.

The ledger stores each certification as an *annotated* tag whose message is the
entry JSON. Annotated tags are objects (they carry a message + tagger), so the
JSON travels with the tag and is fetched with ``git fetch --tags``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(args: list[str], repo: str | Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout


def list_tags(repo: str | Path, prefix: str) -> list[str]:
    """All tag names under ``prefix`` (e.g. ``certified/``)."""
    out = _run(
        ["for-each-ref", "--format=%(refname:short)", f"refs/tags/{prefix}*"],
        repo,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def tag_message(repo: str | Path, tag: str) -> str:
    """The annotation body of an annotated tag (the JSON we stored)."""
    # %(contents) is the tag message for an annotated tag; strip the trailing
    # newline git appends.
    out = _run(["tag", "-l", "--format=%(contents)", tag], repo)
    return out.rstrip("\n")


def tag_exists(repo: str | Path, tag: str) -> bool:
    out = _run(["tag", "-l", tag], repo)
    return bool(out.strip())


def create_annotated_tag(
    repo: str | Path, tag: str, message: str, *, ref: str = "HEAD"
) -> None:
    """Create an annotated tag carrying ``message``.

    Refuses to move an existing tag — ledger entries are append-only and
    immutable (ADR-0001). Re-certifying the same pair is a bug, not an update.
    """
    if tag_exists(repo, tag):
        raise GitError(
            f"tag {tag!r} already exists; ledger entries are append-only and "
            "must never be moved (ADR-0001 immutability rule)"
        )
    _run(["tag", "-a", tag, "-m", message, ref], repo)


def push_tag(repo: str | Path, tag: str, remote: str = "origin") -> None:
    _run(["push", remote, tag], repo)
