#!/bin/sh
# DataHelix solo recipe — container entrypoint.
#
# Boot sequence (proposal §1.7 + §2.1a):
#   1. optional pull-on-boot: sync /project/schemas from SCHEMA_GIT_REMOTE
#      (Mode R), staging + migrate dry-run BEFORE touching the live schemas
#   2. migrate-if-db-exists: apply additive DDL for schema changes
#      (first boot needs no migrate — serve self-initializes the database)
#   3. write Aperture's runtime config.js (ADR-0034 pattern; defaults to the
#      same-origin /graphql seam)
#   4. exec supervisord (nginx + mosaic serve + cors-proxy)
#
# "Restart the container" therefore means: pull (if configured) + migrate +
# serve — the restart-on-migrate model in one motion.
set -eu

PROJECT=/project

# The certified frontier now pins Mosaic ≥0.12.0 (ADR-0004 rename shipped),
# so the CLI is `mosaic`.
MOSAIC_BIN=mosaic
export MOSAIC_BIN

# Resolve the config file explicitly and hand it to serve via --config:
# relying on auto-discovery silently falls back to the default bundled schema
# when no config is found, so we fail loudly instead if the project has none.
if [ -f "$PROJECT/mosaic.yaml" ]; then
  MOSAIC_CONFIG="$PROJECT/mosaic.yaml"
else
  echo "solo: /project has no mosaic.yaml — bind-mount a project directory" >&2
  echo "solo: (see the recipe README; 'make init' scaffolds one)" >&2
  exit 1
fi
export MOSAIC_CONFIG

DB="$PROJECT/data/mosaic.db"
mkdir -p "$PROJECT/data" "$PROJECT/schemas"

# ── 1. Mode R: pull schemas from git before migrating ──────────────────────
if [ -n "${SCHEMA_GIT_REMOTE:-}" ]; then
  echo "solo: syncing schemas from $SCHEMA_GIT_REMOTE (${SCHEMA_GIT_REF:-default branch})"
  STAGING="$(mktemp -d)"
  trap 'rm -rf "$STAGING"' EXIT
  git init -q "$STAGING/repo"
  git -C "$STAGING/repo" remote add origin "$SCHEMA_GIT_REMOTE"
  git -C "$STAGING/repo" fetch -q --depth 1 origin "${SCHEMA_GIT_REF:-HEAD}"
  git -C "$STAGING/repo" checkout -q FETCH_HEAD
  SRC="$STAGING/repo/${SCHEMA_GIT_PATH:-schemas}"
  if [ ! -d "$SRC" ]; then
    echo "solo: ABORT — '$SCHEMA_GIT_PATH' not found in the remote (set SCHEMA_GIT_PATH)" >&2
    exit 1
  fi
  # Dry-run against the staged checkout BEFORE replacing the live schemas:
  # a failure leaves both the database and the old schema dir untouched.
  if [ -f "$DB" ]; then
    if ! "$MOSAIC_BIN" migrate --dry-run --schema-dir "$SRC" --db-path "$DB"; then
      echo "solo: ABORT — staged schemas fail migration planning; live schemas untouched." >&2
      echo "solo: inspect with '$MOSAIC_BIN schema safe-deploy' against the remote checkout." >&2
      exit 1
    fi
  fi
  # Swap: replace the live schema dir contents with the staged checkout.
  find "$PROJECT/schemas" -mindepth 1 -delete
  cp -a "$SRC/." "$PROJECT/schemas/"
  echo "solo: schemas synced ($(ls "$PROJECT/schemas" | wc -l) files)"
fi

# ── 2. Migrate-if-db-exists ─────────────────────────────────────────────────
if [ -f "$DB" ]; then
  echo "solo: existing database found — applying schema migrations"
  "$MOSAIC_BIN" migrate --schema-dir "$PROJECT/schemas" --db-path "$DB"
else
  echo "solo: first boot — database will be initialized by mosaic serve"
fi

# ── 3. Aperture runtime config (ADR-0034) ──────────────────────────────────
# Same vocabulary as the Aperture image's own 40-aperture-config.sh, with the
# same-origin seam as the default endpoint.
: "${VITE_HIPPO_GRAPHQL_URL:=/graphql}"
export VITE_HIPPO_GRAPHQL_URL
OUT=/srv/aperture/config.js
{
  printf 'window.__APERTURE_CONFIG__ = {'
  sep=''
  for key in VITE_HIPPO_GRAPHQL_URL VITE_HIPPO_CONTROL_PLANE_URL VITE_WORKFLOWS VITE_NAV; do
    value=$(printenv "$key" 2>/dev/null || true)
    if [ -n "$value" ]; then
      escaped=$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g')
      printf '%s\n  "%s": "%s"' "$sep" "$key" "$escaped"
      sep=','
    fi
  done
  printf '\n};\n'
} > "$OUT"
echo "solo: aperture runtime config written (endpoint: $VITE_HIPPO_GRAPHQL_URL)"

# ── 4. Serve ────────────────────────────────────────────────────────────────
exec supervisord -n -c /etc/supervisor/supervisord.conf
