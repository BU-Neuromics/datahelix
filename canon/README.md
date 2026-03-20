# Canon

Semantic dependency resolver and workflow orchestrator for the BASS platform.

Canon queries Hippo for existing entities matching a metadata specification (REUSE)
or builds an execution plan using production rules (BUILD), then delegates execution
to workflow executor adapters (Nextflow, Snakemake, Cromwell, LocalProcess).

## Install

```bash
pip install canon
```

## Quick start

```bash
canon plan --target AlignmentFile --metadata aligner=STAR genome_build=GRCh38 sample_id=AD-001
canon run  --target AlignmentFile --metadata aligner=STAR genome_build=GRCh38 sample_id=AD-001
canon status
```

See [docs/](docs/) for full documentation.
