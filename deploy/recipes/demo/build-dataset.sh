#!/bin/sh
# Demo recipe — build-time dataset generation + preload (runs in the `data`
# stage, inside the pinned Mosaic/Hippo image, so the DB is built by the exact
# version that serves it — zero skew). Produces /project: schemas/, mosaic.yaml,
# and a pre-loaded data/mosaic.db.
set -eu

SCHEMA_REPO_DIR=${SCHEMA_REPO_DIR:-/build/brainbank-hippo-schema}
SCHEMA_SUBDIR=${SCHEMA_SUBDIR:-schema}
TREE_ROOT_FILE=${TREE_ROOT_FILE:-brainbank.yaml}
PROJECT=/project
SEED=${DEMO_SEED:-0}
# Per-collection scale; override via build args. Defaults are "visibly large"
# but keep the CI build tractable.
COUNTS=${DEMO_COUNTS:-donors=500 samples=3000 datasets=800 assays=800 processes=400 analyses=200}

mkdir -p "$PROJECT/schemas" "$PROJECT/data"
cp -a "$SCHEMA_REPO_DIR/$SCHEMA_SUBDIR/." "$PROJECT/schemas/"
SCHEMA="$PROJECT/schemas/$TREE_ROOT_FILE"

echo "build-dataset: generating (seed=$SEED, counts: $COUNTS)"
# shellcheck disable=SC2086
linkml-data-gen "$SCHEMA" --seed "$SEED" --count-for $COUNTS -o /tmp/raw.yaml

echo "build-dataset: remapping accessors to Mosaic's ingest bundle"
python3 /build/remap_accessors.py "$SCHEMA" /tmp/raw.yaml /tmp/bundle.yaml

# Config: point schema_path at the tree-root FILE so its cross-file imports
# resolve; pin the sqlite path (version-agnostic — see the solo recipe).
cat > "$PROJECT/mosaic.yaml" <<EOF
schema_path: schemas/$TREE_ROOT_FILE
storage_backend: sqlite
database_url: data/mosaic.db
EOF

# Ingest straight into the canonical SQLite path. Mosaic 0.12.0's ingest
# takes --db-path and defers foreign-key checks to commit (mosaic #95), so the
# brain-bank reference cycles (Container.parent, Location.parent_location,
# AnatomicalStructure.part_of) load atomically. Run from the project dir so
# the schema's relative imports and the DB path resolve consistently.
echo "build-dataset: ingesting (cwd=$PROJECT)"
cd "$PROJECT"
mosaic ingest --file /tmp/bundle.yaml --db-path data/mosaic.db --validate-schema "$SCHEMA"
[ -f data/mosaic.db ] || { echo "build-dataset: no database produced by ingest" >&2; exit 1; }

rm -f /tmp/raw.yaml /tmp/bundle.yaml
echo "build-dataset: done — $(du -h data/mosaic.db | cut -f1) database baked"
