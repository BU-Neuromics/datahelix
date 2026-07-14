#!/bin/sh
# DataHelix demo recipe — entrypoint. The dataset is baked into the image, so
# there is no migrate/pull loop: resolve the config, write Aperture's runtime
# config (same-origin /graphql), and serve.
set -eu

PROJECT=/project

MOSAIC_BIN="$(command -v mosaic || command -v hippo)"
[ -n "$MOSAIC_BIN" ] || { echo "demo: no mosaic/hippo CLI found" >&2; exit 1; }
export MOSAIC_BIN

if [ -f "$PROJECT/mosaic.yaml" ]; then
  MOSAIC_CONFIG="$PROJECT/mosaic.yaml"
elif [ -f "$PROJECT/hippo.yaml" ]; then
  MOSAIC_CONFIG="$PROJECT/hippo.yaml"
else
  echo "demo: /project has no config — image build is broken" >&2
  exit 1
fi
export MOSAIC_CONFIG

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
echo "demo: aperture runtime config written (endpoint: $VITE_HIPPO_GRAPHQL_URL)"

exec supervisord -n -c /etc/supervisor/supervisord.conf
