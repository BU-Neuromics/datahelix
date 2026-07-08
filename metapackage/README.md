# datahelix

Thin metapackage for the DataHelix platform (platform ADR-0002). `pip install
datahelix` pulls in the non-optional foundation (Mosaic, the LinkML runtime);
optional components are extras:

```
pip install datahelix[canon]
pip install datahelix[cappella]
pip install datahelix[aperture]
pip install datahelix[all]      # canon + cappella + aperture
```

This package owns two things and nothing else:

1. **The version-compatibility matrix** — a `datahelix` release pins tested
   ranges of the independently-versioned component distributions.
2. **A small umbrella CLI**, `datahelix`, with two introspection-only
   subcommands:
   - `datahelix info` — table of platform components: installed?, version.
   - `datahelix doctor` — import-checks installed components and reports
     `mosaic.*` entry-point group counts; exits nonzero if an installed
     component fails to import.

No entity, storage, or transform logic lives here. See
[`../platform/design/decisions/ADR-0002-datahelix-metapackage-and-extras.md`](../platform/design/decisions/ADR-0002-datahelix-metapackage-and-extras.md)
for the full rationale.

## Development

`datahelix-mosaic` is not published yet, so a plain `uv run` in this
directory will fail dependency resolution against the project's own
`[project.dependencies]` pin. Run the smoke tests without syncing the
project's declared dependencies instead:

```
cd metapackage
uv run --no-project --with pytest pytest tests/ -q
```

Build still works normally (it does not resolve dependencies):

```
uv build metapackage/
```
