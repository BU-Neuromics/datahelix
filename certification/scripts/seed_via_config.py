"""Seed the certification fixture through mosaic's config-driven factory.

Runs INSIDE the pinned mosaic container (piped to ``python -`` by
run_composition.sh). ``mosaic ingest`` cannot be used here: the CLI builds its
client directly (SQLite default) and never reads ``/app/mosaic.yaml``, so it
would write to a throwaway SQLite file instead of the postgres deployment
that ``mosaic serve`` is reading. This wires the same ingest function to the
same config the server booted with.

Import compatibility (decision 1.7 alias, same as read_lock.py / the ledger):
the composition pins artifacts by digest and never rebuilds them (ADR-0001),
so the currently certified frontier is a pre-rename image (hippo <= 0.10.x)
whose package is still ``hippo``. Prefer the canonical ``mosaic`` package
(>= 0.11.0), fall back to ``hippo`` — falling back also avoids tripping the
renamed image's deprecation shim.
"""

import sys

try:
    from mosaic.cli.commands.ingest import ingest_linkml_yaml
    from mosaic.config import load_mosaic_config as load_config
    from mosaic.core.factory import build_schema_registry, create_client_from_config
except ModuleNotFoundError:  # pre-rename pinned image (hippo <= 0.10.x)
    from hippo.cli.commands.ingest import ingest_linkml_yaml
    from hippo.config import load_hippo_config as load_config
    from hippo.core.factory import build_schema_registry, create_client_from_config

CONFIG = "/app/mosaic.yaml"
SEED = "/app/seed/seed.yaml"

cfg = load_config(CONFIG)
client = create_client_from_config(cfg)
registry = build_schema_registry(cfg.schema_path, merge_requires=True)

result = ingest_linkml_yaml(SEED, client, registry)
print(
    f"seeded {SEED}: created={result.created} "
    f"updated={result.updated} errors={result.errors}"
)
for message in result.error_messages:
    print(f"  - {message}", file=sys.stderr)
sys.exit(1 if result.errors else 0)
