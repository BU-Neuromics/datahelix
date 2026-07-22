#!/usr/bin/env python3
"""Verify the solo Dockerfile's image pins match the certified composition lock.

The solo bundle is "built from a certified pair" (proposal §4.4 middle path):
its Dockerfile pins component images by digest, and those digests MUST be the
ones the certification ledger certified — i.e. exactly what
certification/composition.lock.json pins. This check makes drift a CI failure
instead of a silent lie; the full ledger gate (deploy_gate.sh) then verifies
the lock itself against the ledger.

Usage: check_pins.py [dockerfile] [lockfile]   (defaults resolve from repo layout)
Exit codes: 0 = pins match; 1 = drift or parse failure.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent


def main() -> int:
    dockerfile = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Dockerfile"
    lockfile = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else REPO / "certification" / "composition.lock.json"
    )

    text = dockerfile.read_text()
    args = dict(
        re.findall(r"^ARG\s+(MOSAIC_IMAGE|APERTURE_IMAGE)=(\S+)", text, re.MULTILINE)
    )
    lock = json.loads(lockfile.read_text())["components"]

    ok = True
    for component, arg in (("mosaic", "MOSAIC_IMAGE"), ("aperture", "APERTURE_IMAGE")):
        pinned = args.get(arg)
        certified = f"{lock[component]['image']}@{lock[component]['digest']}"
        if pinned != certified:
            print(f"PIN DRIFT [{component}]:", file=sys.stderr)
            print(f"  Dockerfile {arg}={pinned}", file=sys.stderr)
            print(f"  lock       {certified}", file=sys.stderr)
            ok = False
        else:
            print(f"pin ok [{component}]: {certified}")

    if not ok:
        print(
            "\nThe solo bundle must be built from the certified pair "
            "(certification/composition.lock.json). Update the Dockerfile ARGs "
            "or certify the new pair first (platform ADR-0001).",
            file=sys.stderr,
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
