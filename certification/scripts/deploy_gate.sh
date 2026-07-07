#!/usr/bin/env bash
# Deploy-side ledger gate (platform ADR-0001).
#
# Whatever installs a composition MUST run this before proceeding. It refuses
# any component pair not present as a PASSING ledger entry, and verifies the
# artifact digests match what was certified (a re-cut release is rejected).
#
# Wire it into your deploy tooling as a pre-flight, e.g. at the top of a
# `helm upgrade` / `docker compose up` wrapper:
#
#     certification/scripts/deploy_gate.sh certification/composition.lock.json || exit 1
#
# Exit codes: 0 = certified, deploy may proceed; 2 = blocked; 1 = usage/pins error.
set -euo pipefail

LOCK="${1:-certification/composition.lock.json}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$(dirname "$HERE")"
REPO_DIR="$(dirname "$CERT_DIR")"

# Resolve the pins the deployment intends to install.
eval "$(python3 "$HERE/read_lock.py" "$LOCK" | sed 's/^/PIN_/')"

if [ "${PIN_published:-false}" != "true" ]; then
  echo "DEPLOY BLOCKED: composition pins carry no artifact digests — the pair is"
  echo "not published/certifiable yet. A certified pair must pin digests (ADR-0001)." >&2
  exit 2
fi

# Delegate to the ledger gate (reads certified/* tags in the DataHelix repo).
export PYTHONPATH="$CERT_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m ledger.cli --repo "$REPO_DIR" gate \
  --component "aperture=${PIN_aperture_version}@${PIN_aperture_digest}" \
  --component "hippo=${PIN_hippo_version}@${PIN_hippo_digest}"
