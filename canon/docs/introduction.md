# Canon — Introduction

Canon is the **artifact resolver** for the DataHelix platform. It answers one question:

> *Does this computational result already exist, and if not, how do I produce it?*

A "result" in Canon is defined by its **semantic identity** — the entity type, the sample, the
reference genome, the tool version, and the key parameters — not by a file path. Two RNA-seq
alignment BAMs produced from the same sample, reference, and tool version with the same
parameters are the same artifact, no matter when or where they were produced.

## What Canon Does

When you ask Canon for an artifact:

1. **Looks it up in Hippo.** If a Hippo entity matching the specification already exists, Canon
   returns its URI immediately. No computation is performed.

2. **Plans the computation.** If the artifact does not exist, Canon finds the matching rule in
   `canon_rules.yaml`, recursively resolves that rule's inputs the same way, and builds a
   complete execution plan.

3. **Runs the workflow.** Canon submits the CWL workflow to your configured executor
   (`cwltool`, Toil, or another plugin adapter).

4. **Ingests the result.** After execution, Canon registers the output as a new Hippo entity
   and records a `WorkflowRun` provenance event linking inputs, outputs, tool versions, and
   execution metadata.

## Key Concepts

**Artifact spec** — an entity type plus a set of named parameters. Parameters can be scalar
values (`min_length=20`) or references to Hippo entities
(`genome_build=ref:GenomeBuild{name=GRCh38}`). Entity references create a graph of
dependencies that Canon traverses automatically.

**Rule** — a mapping from an artifact spec to a CWL workflow in `canon_rules.yaml`. Each rule
declares the output entity type it produces and the named inputs it requires. Canon matches
incoming `get` requests to rules by entity type and parameter set.

**REUSE vs. BUILD** — Canon's two resolution outcomes. REUSE means a matching entity was found
in Hippo; BUILD means the workflow will run. The `canon plan` command shows which outcome
Canon would choose without actually running anything.

**WorkflowRun** — a Hippo provenance entity Canon writes after every successful execution. It
records the rule used, input entity IDs, output entity ID, executor, wall time, and a link to
the raw CWL output log. WorkflowRuns form the audit trail for all computed artifacts.

## What Canon Does Not Do

- **Cohort management** — scheduling the same analysis across many samples is Cappella's job.
  Canon resolves one artifact at a time; Cappella coordinates across batches.
- **Data ingestion** — loading raw data files and study metadata is Hippo's job via the
  ingestion pipeline.
- **Workflow authoring** — Canon runs CWL workflows but does not write them. You provide your
  own CWL files (or use community-published workflows).

## Relationship to Snakemake and Nextflow

Canon is a layer above Snakemake and Nextflow, not a replacement. Your existing CWL-wrapped
workflows run unchanged inside Canon. Canon adds the registry lookup layer (skip computation
when the result already exists) and the provenance layer (every run recorded in Hippo).

## Next Steps

- [Quickstart](quickstart.md) — install Canon and resolve your first artifact in under
  10 minutes.
- [User Guide](user-guide.md) — a complete RNA-seq analysis walkthrough from raw FASTQs to
  differential expression, using Canon end-to-end.
