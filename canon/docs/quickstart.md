# Canon — Quickstart

This guide walks you through installing Canon, connecting it to a running Hippo instance, and
resolving your first artifact in around 10 minutes.

## Prerequisites

- Python 3.11 or later
- A running Hippo instance (see [Hippo quickstart](../../hippo/docs/quickstart.md) if you
  need one)
- `cwltool` installed for local execution: `pip install cwltool`

## 1. Install Canon

```bash
pip install canon
```

Verify the install:

```bash
canon --version
# canon 0.1.0
```

## 2. Configure Canon

Create a `canon.yaml` in your working directory:

```yaml
# canon.yaml

hippo_url: "http://localhost:8001"
hippo_token: "${HIPPO_TOKEN}"   # set HIPPO_TOKEN in your environment

executor: cwltool               # local execution via cwltool

rules_file: canon_rules.yaml   # rule definitions (see Step 3)

work_dir: /tmp/canon-work       # scratch space for workflow execution

output_storage:
  type: local
  path: /data/canon-outputs     # where output files are written after execution

log_level: INFO
```

Export your Hippo token (from `hippo token create --label canon-local`):

```bash
export HIPPO_TOKEN=<your-hippo-api-token>
```

## 3. Install Canon's Reference Schema

Canon needs a set of base entity types in Hippo (`Tool`, `ToolVersion`, `GenomeBuild`,
`GeneAnnotation`, `WorkflowRun`). Install them once:

```bash
hippo reference install canon
```

This adds Canon's entity types to your Hippo schema without affecting any existing types.

## 4. Write a Simple Rule

Create `canon_rules.yaml` with a minimal rule. This example produces a `CountMatrix` from a
`FastqFile`:

```yaml
# canon_rules.yaml

rules:
  - name: count_matrix_from_fastq
    produces: CountMatrix
    requires:
      - name: sample
        entity_type: Sample
      - name: genome_build
        entity_type: GenomeBuild
      - name: annotation
        entity_type: GeneAnnotation
      - name: aligner_version
        entity_type: ToolVersion
    workflow: workflows/rnaseq_count.cwl
    output_field: count_matrix_file
```

(You will supply the actual CWL workflow. See the
[User Guide](user-guide.md) for a complete RNA-seq example with real CWL files.)

## 5. Check What Canon Would Do

Before running anything, use `canon plan` to see the REUSE/BUILD decision:

```bash
canon plan CountMatrix \
  sample=ref:Sample{external_id=AD001} \
  genome_build=ref:GenomeBuild{name=GRCh38} \
  annotation=ref:GeneAnnotation{name=GENCODE_v44} \
  aligner_version=ref:ToolVersion{tool=STAR,version=2.7.11a}
```

Expected output (first run, nothing in registry yet):

```
Canon plan — CountMatrix
  sample         → Sample AD001 (uuid: 11a2b3c4-...)   FOUND
  genome_build   → GenomeBuild GRCh38 (uuid: 22b3c4d5-...)   FOUND
  annotation     → GeneAnnotation GENCODE_v44 (uuid: 33c4d5e6-...)   FOUND
  aligner_version → ToolVersion STAR 2.7.11a (uuid: 44d5e6f7-...)   FOUND

Decision: BUILD
  Rule: count_matrix_from_fastq
  Workflow: workflows/rnaseq_count.cwl
  Inputs resolved: 4/4
  Estimated run: ~30min (cwltool, local)
```

## 6. Resolve the Artifact

Run the actual resolution:

```bash
canon get CountMatrix \
  sample=ref:Sample{external_id=AD001} \
  genome_build=ref:GenomeBuild{name=GRCh38} \
  annotation=ref:GeneAnnotation{name=GENCODE_v44} \
  aligner_version=ref:ToolVersion{tool=STAR,version=2.7.11a}
```

Canon will:
1. Confirm the artifact does not exist in Hippo
2. Resolve all required inputs from Hippo
3. Submit the CWL workflow to `cwltool`
4. Ingest the output `CountMatrix` entity into Hippo
5. Record a `WorkflowRun` provenance entity

On completion:

```
✓ CountMatrix resolved
  Entity:  CountMatrix/5e6f7a8b-...
  URI:     file:///data/canon-outputs/AD001_GRCh38_GENCODE_v44_STAR2711a/counts.tsv
  Run:     WorkflowRun/6f7a8b9c-...  (runtime: 27m 14s)
```

## 7. Run the Same Command Again

The second invocation returns immediately:

```bash
canon get CountMatrix \
  sample=ref:Sample{external_id=AD001} \
  genome_build=ref:GenomeBuild{name=GRCh38} \
  annotation=ref:GeneAnnotation{name=GENCODE_v44} \
  aligner_version=ref:ToolVersion{tool=STAR,version=2.7.11a}
```

```
✓ CountMatrix resolved (REUSE)
  Entity:  CountMatrix/5e6f7a8b-...
  URI:     file:///data/canon-outputs/AD001_GRCh38_GENCODE_v44_STAR2711a/counts.tsv
```

No workflow was submitted. Canon found the existing entity in Hippo and returned its URI.

## 8. View Recent Runs

```bash
canon status
```

```
Recent WorkflowRuns (last 10):

  6f7a8b9c-...  CountMatrix  STAR 2.7.11a  AD001  2026-09-15T14:32:00Z  27m14s  ✓
```

## Next Steps

- [User Guide](user-guide.md) — complete RNA-seq analysis from raw FASTQs to differential
  expression, with real CWL workflows and Hippo entity setup.
- For multi-sample batch runs, see the
  [Cappella documentation](../../cappella/docs/quickstart.md).
