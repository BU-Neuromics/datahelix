"""Seed the certification fixture through hippo's config-driven factory.

Runs INSIDE the pinned hippo container (piped to ``python -`` by
run_composition.sh). ``hippo ingest`` cannot be used here: the CLI builds its
client directly (SQLite default) and never reads ``/app/hippo.yaml``, so it
would write to a throwaway SQLite file instead of the postgres deployment
that ``hippo serve`` is reading. This wires the same ingest function to the
same config the server booted with.
"""

import sys

from hippo.cli.commands.ingest import ingest_linkml_yaml
from hippo.config import load_hippo_config
from hippo.core.factory import build_schema_registry, create_client_from_config

CONFIG = "/app/hippo.yaml"
SEED = "/app/seed/seed.yaml"

cfg = load_hippo_config(CONFIG)
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
