#!/usr/bin/env python3
"""Resolve certification pins from composition.lock.json (or dispatch inputs).

Emits shell-eval'able assignments and, when run in CI, appends the same keys to
$GITHUB_OUTPUT. A pin whose digest is null/placeholder marks the composition
"unpublished" so the workflow skips the boot as an honest no-op (ADR-0001: never
certify an artifact that isn't published by digest).

Usage:
    read_lock.py path/to/composition.lock.json
    read_lock.py --hippo-version X --hippo-digest D \
                 --aperture-version Y --aperture-digest D2 [--line frontier]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _emit(pairs: dict[str, str]) -> None:
    for k, v in pairs.items():
        print(f"{k}={v}")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as fh:
            for k, v in pairs.items():
                fh.write(f"{k}={v}\n")


def _is_real_digest(d) -> bool:
    return isinstance(d, str) and (":" in d or d.startswith("sha256-")) and "placeholder" not in d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lock", nargs="?", help="composition.lock.json")
    ap.add_argument("--hippo-version")
    ap.add_argument("--hippo-digest")
    ap.add_argument("--aperture-version")
    ap.add_argument("--aperture-digest")
    ap.add_argument("--line")
    ap.add_argument("--fixture-version", default="1.0.0")
    args = ap.parse_args(argv)

    if args.lock:
        doc = json.loads(Path(args.lock).read_text())
        comps = doc["components"]
        pins = {
            "line": doc.get("line", "frontier"),
            "fixture_version": doc.get("fixture_version", args.fixture_version),
            "hippo_version": comps["hippo"]["version"],
            "hippo_digest": comps["hippo"].get("digest") or "",
            "hippo_image": comps["hippo"].get("image", ""),
            "aperture_version": comps["aperture"]["version"],
            "aperture_digest": comps["aperture"].get("digest") or "",
            "aperture_image": comps["aperture"].get("image", ""),
        }
    else:
        pins = {
            "line": args.line or "frontier",
            "fixture_version": args.fixture_version,
            "hippo_version": args.hippo_version or "",
            "hippo_digest": args.hippo_digest or "",
            "hippo_image": "ghcr.io/bu-neuromics/hippo",
            "aperture_version": args.aperture_version or "",
            "aperture_digest": args.aperture_digest or "",
            "aperture_image": "ghcr.io/bu-neuromics/aperture",
        }

    published = _is_real_digest(pins["hippo_digest"]) and _is_real_digest(pins["aperture_digest"])
    pins["published"] = "true" if published else "false"
    if published:
        pins["hippo_ref"] = f"{pins['hippo_image']}@{pins['hippo_digest']}"
        pins["aperture_ref"] = f"{pins['aperture_image']}@{pins['aperture_digest']}"
    _emit(pins)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
