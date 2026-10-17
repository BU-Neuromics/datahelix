#!/bin/sh
# demo-reel recipe — build-time generation + preload of the mosaic-demo-small
# dataset (DEMO_DATASET=small). Runs in the `data-small` stage, inside the
# pinned Mosaic image, so the DB is built by the exact version that serves it.
# Mirrors that repo's own `make generate migrate ingest`; produces /project.
set -eu

SRC=${SMALL_DIR:-/build/mosaic-demo-small}
PROJECT=/project
SEED=${DEMO_SEED:-0}

mkdir -p "$PROJECT/schemas" "$PROJECT/data"
cp -a "$SRC/schemas/." "$PROJECT/schemas/"

echo "build-small: generating (seed=$SEED)"
# generate.py resolves hints.yaml and generation_schema.yaml next to itself.
python3 "$SRC/generate.py" --seed "$SEED" --out /tmp/bundle.yaml

cat > "$PROJECT/mosaic.yaml" <<EOF
schema_path: schemas/
storage_backend: sqlite
database_url: data/mosaic.db
EOF

cd "$PROJECT"
echo "build-small: migrating"
: > data/mosaic.db
mosaic migrate --schema-dir schemas --db-path data/mosaic.db
echo "build-small: ingesting"
mosaic ingest --file /tmp/bundle.yaml --db-path data/mosaic.db --validate-schema schemas

rm -f /tmp/bundle.yaml

# Discovery cases travel with the schema they describe (`make eval`): the
# frozen eleven plus the new-collections arm, as one list. Both files are a
# single top-level block sequence, so concatenation is a valid merge.
mkdir -p "$PROJECT/evals"
cat "$SRC/evals/discovery.yaml" "$SRC/evals/discovery-new-collections.yaml" \
  > "$PROJECT/evals/discovery.yaml"
echo "build-small: done — $(du -h data/mosaic.db | cut -f1) database baked"
