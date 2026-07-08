#!/usr/bin/env bash
# Boot the pinned composition, seed the fixture, run the golden-path suite under
# the wall-clock budget, and emit a result. Reusable by the certify workflow on
# main, on maintenance branches, and for workflow_dispatch backfills
# (platform ADR-0001).
#
# Required env:
#   HIPPO_IMAGE      <image>@<digest>   (pull-by-digest; never build from source)
#   APERTURE_IMAGE   <image>@<digest>
# Optional:
#   BUDGET_SECONDS   hard wall-clock budget for the whole run (default 600 = ~10m)
#   RESULT_FILE      where to write the result JSON (default certification/result.json)
#
# Exit code: 0 = pass, non-zero = fail. The result JSON always carries a
# `failing_check` on failure (the ledger records failures too).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$(dirname "$HERE")"
COMPOSE="$CERT_DIR/compose/docker-compose.certify.yml"
BUDGET_SECONDS="${BUDGET_SECONDS:-600}"
RESULT_FILE="${RESULT_FILE:-$CERT_DIR/result.json}"
START="$(date +%s)"

result() {  # result <pass|fail> <failing_check|"">
  local status="$1" check="$2"
  local elapsed=$(( $(date +%s) - START ))
  printf '{"result":"%s","failing_check":%s,"elapsed_seconds":%d,"budget_seconds":%d}\n' \
    "$status" \
    "$( [ -n "$check" ] && printf '"%s"' "$check" || printf 'null' )" \
    "$elapsed" "$BUDGET_SECONDS" > "$RESULT_FILE"
  echo "== certification $status (${elapsed}s / ${BUDGET_SECONDS}s budget) =="
  docker compose -f "$COMPOSE" logs --no-color hippo aperture 2>/dev/null | tail -50 || true
  docker compose -f "$COMPOSE" down -v >/dev/null 2>&1 || true
  [ "$status" = "pass" ]
}

# Enforce the budget over the whole run.
run_step() {  # run_step <name> <cmd...>
  local name="$1"; shift
  local remaining=$(( BUDGET_SECONDS - ($(date +%s) - START) ))
  if (( remaining <= 0 )); then
    echo "budget exhausted before $name"; return 124
  fi
  timeout "${remaining}s" "$@"
}

: "${HIPPO_IMAGE:?set HIPPO_IMAGE=<image>@<digest>}"
: "${APERTURE_IMAGE:?set APERTURE_IMAGE=<image>@<digest>}"
export HIPPO_IMAGE APERTURE_IMAGE

echo "== pulling pinned artifacts by digest =="
run_step pull docker compose -f "$COMPOSE" pull postgres hippo aperture || { result fail "artifact-pull"; exit 1; }

echo "== booting postgres + hippo (serve --graphql over fixture schema) =="
run_step boot docker compose -f "$COMPOSE" up -d postgres hippo || { result fail "hippo-boot"; exit 1; }

# Wait for hippo health within budget.
echo "== waiting for hippo health =="
# "(healthy)" — plain `healthy` also matches "(unhealthy)", which let the
# first real boot sail past a failing healthcheck (PR #45). An unhealthy
# verdict fails fast instead of burning the budget.
until docker compose -f "$COMPOSE" ps hippo | grep -q '(healthy)'; do
  if docker compose -f "$COMPOSE" ps hippo | grep -q '(unhealthy)'; then
    result fail "hippo-health"; exit 1
  fi
  (( $(date +%s) - START >= BUDGET_SECONDS )) && { result fail "hippo-health"; exit 1; }
  sleep 2
done

echo "== seeding bootstrap fixture =="
# Not `hippo ingest`: the CLI builds a SQLite-default client and never reads
# /app/hippo.yaml, so it would write to a throwaway SQLite file instead of the
# postgres deployment `hippo serve` is reading. seed_via_config.py runs the
# same ingest wired to the booted config.
run_step seed bash -c \
  "docker compose -f '$COMPOSE' exec -T hippo python - < '$HERE/seed_via_config.py'" \
  || { result fail "fixture-seed"; exit 1; }

echo "== bringing up aperture SPA =="
run_step aperture docker compose -f "$COMPOSE" up -d aperture || { result fail "aperture-boot"; exit 1; }

echo "== running golden-path scenarios =="
# The Playwright suite enforces its own per-run timeout too (playwright.config.ts).
if run_step scenarios bash -c "cd '$CERT_DIR/scenarios' && npm ci && npx playwright install --with-deps chromium && npx playwright test"; then
  result pass ""
  exit 0
else
  code=$?
  [ "$code" = "124" ] && result fail "time-budget" || result fail "golden-path-scenarios"
  exit 1
fi
