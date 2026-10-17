#!/usr/bin/env python3
"""Verify demo-reel's image pins: the certified pair, and the uncertified planner.

Two classes of pin, checked differently:

  certified   MOSAIC_IMAGE / APERTURE_IMAGE in the Dockerfile MUST equal what
              certification/composition.lock.json pins — the data image is a
              certified-pair build, exactly as `demo` is. Drift fails.

  planner     the `reel` service image in docker-compose.yml MUST be
              digest-pinned (a tag alone is a claim, not evidence), but it is
              NOT in the composition lock, so there is nothing to compare it
              to. It is reported as uncertified rather than silently passed.
              If the lock ever gains a `reel` entry, it is compared like the
              others and this distinction goes away on its own.

Usage: check_pins.py [dockerfile] [compose] [lockfile]   (defaults resolve from repo layout)
Exit codes: 0 = pins ok; 1 = drift, an undigested planner, or parse failure.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent


def main() -> int:
    dockerfile = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Dockerfile"
    compose = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "docker-compose.yml"
    lockfile = (
        Path(sys.argv[3])
        if len(sys.argv) > 3
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

    # The planner: the one `image:` line naming reel in the compose file.
    m = re.search(r"^\s*image:\s*(\S*/reel(?::[^@\s]+)?(?:@(sha256:[0-9a-f]{64}))?)\s*$",
                  compose.read_text(), re.MULTILINE)
    if not m:
        print("PLANNER PIN: no reel image found in docker-compose.yml", file=sys.stderr)
        ok = False
    elif not m.group(2):
        print(f"PLANNER PIN: {m.group(1)} is not digest-pinned", file=sys.stderr)
        ok = False
    elif "reel" in lock:
        certified = f"{lock['reel']['image']}@{lock['reel']['digest']}"
        image_at_digest = re.sub(r":[^@/]+@", "@", m.group(1))
        if image_at_digest != certified:
            print(f"PIN DRIFT [reel]:\n  compose {m.group(1)}\n  lock    {certified}", file=sys.stderr)
            ok = False
        else:
            print(f"pin ok [reel]: {certified}")
    else:
        print(f"pin UNCERTIFIED [reel]: {m.group(1)}")
        print("  digest-pinned, but the composition lock has no reel entry — the planner")
        print("  is outside the ADR-0001 gate. Fine for a demo; not a certified deployment.")

    if not ok:
        print(
            "\nThe demo-reel data image must be built from the certified pair "
            "(certification/composition.lock.json), and the planner must be "
            "digest-pinned. Update the pins or certify the new pair first "
            "(platform ADR-0001).",
            file=sys.stderr,
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
