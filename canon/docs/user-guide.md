# Canon — User Guide: RNA-seq Analysis Walkthrough

This guide walks through a complete bulk RNA-seq analysis using Canon, from raw FASTQ files to
a count matrix, using three DLPFC (dorsolateral prefrontal cortex) samples from a small
Alzheimer's disease study.

**Pipeline:**
```
raw FASTQs → cutadapt (trim) → STAR (align) → HTSeq-count → gene counts
```

By the end of this guide you will have:
- All required Hippo reference entities registered
- A complete `canon_rules.yaml` with three rules (trim → align → count)
- Resolved count matrices for three samples, with full provenance in Hippo
- Hands-on experience with `canon get`, `canon plan`, and `canon status`

## Prerequisites

- Canon and `cwltool` installed (`pip install canon cwltool`)
- A running Hippo instance with Canon's reference schema installed:
  `hippo reference install canon`
- FASTQ files accessible at S3 or local paths
- See [Quickstart](quickstart.md) for the initial setup steps

---

## Part 1: Register Reference Data in Hippo

Before Canon can resolve any artifacts, the reference entities (tools, genome builds,
annotations, samples, and raw data files) must exist in Hippo.

### 1.1 Tools and Tool Versions

```bash
# Tools (the software itself)
hippo entity create Tool --name STAR \
  --category aligner --biotools-id STAR --bioconda-name star

hippo entity create Tool --name cutadapt \
  --category trimmer --biotools-id cutadapt --bioconda-name cutadapt

hippo entity create Tool --name HTSeq \
  --category counter --biotools-id HTSeq --bioconda-name htseq

# Tool versions (pinned releases used in this study)
hippo entity create ToolVersion --name STAR --version 2.7.11a \
  --bioconda-build "2.7.11a--h9ee0642_0" --release-date 2023-11-01

hippo entity create ToolVersion --name cutadapt --version 4.6 \
  --bioconda-build "4.6--py311h38fbfac_1" --release-date 2023-10-15

hippo entity create ToolVersion --name HTSeq --version 2.0.5 \
  --bioconda-build "2.0.5--py311h38fbfac_0" --release-date 2023-09-01
```

### 1.2 Genome Build and Annotation

```bash
hippo entity create GenomeBuild --name GRCh38 --patch p14 \
  --species "Homo sapiens" --ucsc-name hg38 \
  --ncbi-accession GCA_000001405.15 \
  --fasta-uri "s3://lab-references/genomes/GRCh38/GRCh38.primary_assembly.genome.fa" \
  --fai-uri "s3://lab-references/genomes/GRCh38/GRCh38.primary_assembly.genome.fa.fai"

hippo entity create GeneAnnotation --source GENCODE --version 44 \
  --genome-build "ref:GenomeBuild{name=GRCh38}" \
  --release-date 2023-06-01 \
  --gtf-uri "s3://lab-references/annotations/gencode.v44.primary_assembly.annotation.gtf.gz" \
  --gene-count 61852
```

### 1.3 Samples

```bash
for id in DLPFC_001 DLPFC_002 DLPFC_003; do
  hippo entity create Sample --id "$id" \
    --tissue "dorsolateral prefrontal cortex" \
    --species "Homo sapiens" \
    --library-type "bulk RNA-seq" \
    --library-prep "TruSeq Stranded Total RNA"
done
```

### 1.4 Raw FASTQ Files

```bash
hippo entity create FastqFile \
  --sample "ref:Sample{id=DLPFC_001}" \
  --uri "s3://lab-rnaseq-data/raw/DLPFC_001_R1.fastq.gz" \
  --read-number 1 --read-count 45218903

hippo entity create FastqFile \
  --sample "ref:Sample{id=DLPFC_002}" \
  --uri "s3://lab-rnaseq-data/raw/DLPFC_002_R1.fastq.gz" \
  --read-number 1 --read-count 52441287

hippo entity create FastqFile \
  --sample "ref:Sample{id=DLPFC_003}" \
  --uri "s3://lab-rnaseq-data/raw/DLPFC_003_R1.fastq.gz" \
  --read-number 1 --read-count 41887652
```

---

## Part 2: Define Rules in `canon_rules.yaml`

Canon rules map artifact types to CWL workflows. Rules are matched by entity type and
parameter set. Here are the three rules for this pipeline:

```yaml
# canon_rules.yaml

rules:

  # Rule 1: Adapter and quality trimming with cutadapt
  - name: trim_reads
    produces:
      entity_type: TrimmedFastqFile
      match:
        sample: "{sample}"
        trimmer: "ref:ToolVersion{tool.name=cutadapt, version={cutadapt_version}}"
        quality_cutoff: "{quality_cutoff}"
        min_length: "{min_length}"
    requires:
      - bind: raw_fastq
        entity_type: FastqFile
        match:
          sample: "{sample}"
    execute:
      workflow: workflows/cutadapt.cwl
      inputs:
        fastq: "{raw_fastq.uri}"
        quality_cutoff: "{quality_cutoff}"
        min_length: "{min_length}"
        adapter: "AGATCGGAAGAGCACACGTCTGAACTCCAGTCA"
        sample_id: "{sample}"

  # Rule 2: STAR alignment
  - name: align_reads
    produces:
      entity_type: AlignmentFile
      match:
        sample: "{sample}"
        genome_build: "ref:GenomeBuild{name={genome_build}}"
        aligner: "ref:ToolVersion{tool.name=STAR, version={star_version}}"
        trimmer: "ref:ToolVersion{tool.name=cutadapt, version={cutadapt_version}}"
        quality_cutoff: "{quality_cutoff}"
        min_length: "{min_length}"
    requires:
      - bind: trimmed_fastq
        entity_type: TrimmedFastqFile
        match:
          sample: "{sample}"
          trimmer: "ref:ToolVersion{tool.name=cutadapt, version={cutadapt_version}}"
          quality_cutoff: "{quality_cutoff}"
          min_length: "{min_length}"
    execute:
      workflow: workflows/star_align.cwl
      inputs:
        fastq: "{trimmed_fastq.uri}"
        genome_build: "{genome_build}"
        star_version: "{star_version}"
        sample_id: "{sample}"
        threads: 16

  # Rule 3: Gene counting with HTSeq
  - name: count_reads
    produces:
      entity_type: CountMatrix
      match:
        sample: "{sample}"
        genome_build: "ref:GenomeBuild{name={genome_build}}"
        annotation: "ref:GeneAnnotation{source=GENCODE, version={gencode_version}}"
        aligner: "ref:ToolVersion{tool.name=STAR, version={star_version}}"
        counter: "ref:ToolVersion{tool.name=HTSeq, version={htseq_version}}"
        trimmer: "ref:ToolVersion{tool.name=cutadapt, version={cutadapt_version}}"
        quality_cutoff: "{quality_cutoff}"
        min_length: "{min_length}"
    requires:
      - bind: alignment
        entity_type: AlignmentFile
        match:
          sample: "{sample}"
          genome_build: "ref:GenomeBuild{name={genome_build}}"
          aligner: "ref:ToolVersion{tool.name=STAR, version={star_version}}"
          trimmer: "ref:ToolVersion{tool.name=cutadapt, version={cutadapt_version}}"
          quality_cutoff: "{quality_cutoff}"
          min_length: "{min_length}"
      - bind: annotation_file
        entity_type: GeneAnnotationFile
        match:
          annotation: "ref:GeneAnnotation{source=GENCODE, version={gencode_version}}"
    execute:
      workflow: workflows/htseq_count.cwl
      inputs:
        bam: "{alignment.uri}"
        gtf: "{annotation_file.uri}"
        sample_id: "{sample}"
        strand: "reverse"
        mode: "union"
```

---

## Part 3: Plan and Execute

### 3.1 Dry Run with `canon plan`

Before submitting any workflows, inspect Canon's resolution plan for one sample:

```bash
canon plan CountMatrix \
  sample=ref:Sample{id=DLPFC_001} \
  genome_build=GRCh38 \
  gencode_version=44 \
  star_version=2.7.11a \
  htseq_version=2.0.5 \
  cutadapt_version=4.6 \
  quality_cutoff=20 \
  min_length=20
```

First-run output:

```
Canon plan — CountMatrix for DLPFC_001

Step 1: TrimmedFastqFile (DLPFC_001, cutadapt 4.6, q20, l20)
  → BUILD (rule: trim_reads)
  Input: FastqFile DLPFC_001   FOUND (uuid: fa01...)

Step 2: AlignmentFile (DLPFC_001, GRCh38, STAR 2.7.11a)
  → BUILD (rule: align_reads)
  Input: TrimmedFastqFile      will be built in Step 1

Step 3: CountMatrix (DLPFC_001, GRCh38, GENCODE v44, STAR 2.7.11a, HTSeq 2.0.5)
  → BUILD (rule: count_reads)
  Input: AlignmentFile         will be built in Step 2
  Input: GeneAnnotationFile    FOUND (uuid: ge44...)

Total steps: 3 BUILD, 0 REUSE
Estimated runtime: ~90min (cwltool, sequential)
```

### 3.2 Resolve Artifacts for All Three Samples

Run `canon get` for each sample. Canon will resolve each pipeline end-to-end:

```bash
for sample in DLPFC_001 DLPFC_002 DLPFC_003; do
  echo "=== Processing $sample ==="
  canon get CountMatrix \
    sample="ref:Sample{id=$sample}" \
    genome_build=GRCh38 \
    gencode_version=44 \
    star_version=2.7.11a \
    htseq_version=2.0.5 \
    cutadapt_version=4.6 \
    quality_cutoff=20 \
    min_length=20
done
```

Canon automatically reuses the STAR genome index (built once, shared across all samples):

```
=== Processing DLPFC_001 ===
  TrimmedFastqFile DLPFC_001   → BUILD  (cutadapt, 14m)
  AlignmentFile DLPFC_001      → BUILD  (STAR, 31m)
  CountMatrix DLPFC_001        → BUILD  (HTSeq, 8m)
✓ CountMatrix/5e6f7a8b-...   file:///data/canon-outputs/DLPFC_001_counts.tsv

=== Processing DLPFC_002 ===
  TrimmedFastqFile DLPFC_002   → BUILD  (cutadapt, 16m)
  AlignmentFile DLPFC_002      → BUILD  (STAR, 36m)  [StarIndex REUSE]
  CountMatrix DLPFC_002        → BUILD  (HTSeq, 9m)
✓ CountMatrix/6f7a8b9c-...   file:///data/canon-outputs/DLPFC_002_counts.tsv

=== Processing DLPFC_003 ===
  TrimmedFastqFile DLPFC_003   → BUILD  (cutadapt, 13m)
  AlignmentFile DLPFC_003      → BUILD  (STAR, 29m)  [StarIndex REUSE]
  CountMatrix DLPFC_003        → BUILD  (HTSeq, 7m)
✓ CountMatrix/7a8b9c0d-...   file:///data/canon-outputs/DLPFC_003_counts.tsv
```

### 3.3 Re-Run Safety

Running the same commands a second time is safe. Every artifact is found in Hippo and
returned immediately — no workflows are submitted:

```bash
canon get CountMatrix \
  sample="ref:Sample{id=DLPFC_001}" \
  genome_build=GRCh38 gencode_version=44 \
  star_version=2.7.11a htseq_version=2.0.5 \
  cutadapt_version=4.6 quality_cutoff=20 min_length=20
```

```
✓ CountMatrix/5e6f7a8b-...  REUSE  (0.1s)
  URI: file:///data/canon-outputs/DLPFC_001_counts.tsv
```

---

## Part 4: Inspect Provenance

### 4.1 View Recent Runs

```bash
canon status
```

```
Recent WorkflowRuns (last 10):

  UUID          Entity          Rule           Sample     Started                 Runtime  Status
  7a8b9c0d-...  CountMatrix     count_reads    DLPFC_003  2026-09-15T16:41:00Z   7m22s    ✓
  69ab0c1d-...  AlignmentFile   align_reads    DLPFC_003  2026-09-15T16:12:00Z   29m14s   ✓
  58ba0b1c-...  TrimmedFastqFl  trim_reads     DLPFC_003  2026-09-15T15:59:00Z   12m55s   ✓
  6f7a8b9c-...  CountMatrix     count_reads    DLPFC_002  2026-09-15T15:21:00Z   9m03s    ✓
  ...
```

### 4.2 Full Provenance for a Count Matrix

Use Hippo directly to inspect the complete provenance chain for any entity:

```bash
hippo history CountMatrix/5e6f7a8b-...
```

```
Provenance chain: CountMatrix/5e6f7a8b (DLPFC_001)

  EntityCreated     2026-09-15T14:32:00Z
    actor: service:canon-runner
    source_rule: count_reads
    workflow_run: WorkflowRun/6f7a8b9c-...

  ← input: AlignmentFile/4d5e6f7a (DLPFC_001 / GRCh38 / STAR 2.7.11a)
      EntityCreated 2026-09-15T13:51:00Z
        source_rule: align_reads
        workflow_run: WorkflowRun/5e6f7a8b-...

      ← input: TrimmedFastqFile/3c4d5e6f (DLPFC_001 / cutadapt 4.6 / q20 / l20)
            EntityCreated 2026-09-15T13:20:00Z
              source_rule: trim_reads
              workflow_run: WorkflowRun/4d5e6f7a-...

            ← input: FastqFile/0a1b2c3d (DLPFC_001 / R1)
                  EntityCreated 2026-09-01T09:14:00Z
                    actor: data-team
```

The full lineage — from raw FASTQ through trimming and alignment to the count matrix — is
traceable in a single Hippo history query.

### 4.3 Query All Count Matrices Across Samples

```bash
hippo query CountMatrix \
  genome_build="ref:GenomeBuild{name=GRCh38}" \
  annotation="ref:GeneAnnotation{source=GENCODE, version=44}"
```

```
3 entities found:

  CountMatrix/5e6f7a8b  DLPFC_001  GRCh38  GENCODE v44  STAR 2.7.11a  HTSeq 2.0.5
  CountMatrix/6f7a8b9c  DLPFC_002  GRCh38  GENCODE v44  STAR 2.7.11a  HTSeq 2.0.5
  CountMatrix/7a8b9c0d  DLPFC_003  GRCh38  GENCODE v44  STAR 2.7.11a  HTSeq 2.0.5
```

---

## Part 5: Parameter Changes and Re-Analysis

A key strength of Canon's semantic identity model is that changing any parameter automatically
distinguishes new artifacts from existing ones — no manual file management required.

### 5.1 Re-run with a Different Quality Cutoff

```bash
canon plan CountMatrix \
  sample=ref:Sample{id=DLPFC_001} \
  genome_build=GRCh38 gencode_version=44 \
  star_version=2.7.11a htseq_version=2.0.5 \
  cutadapt_version=4.6 quality_cutoff=30 min_length=20
```

Because `quality_cutoff` is part of the artifact's semantic identity, Canon correctly
identifies that no `TrimmedFastqFile` with `quality_cutoff=30` exists and plans a full BUILD:

```
Step 1: TrimmedFastqFile (DLPFC_001, cutadapt 4.6, q30, l20)  → BUILD
Step 2: AlignmentFile    (DLPFC_001, GRCh38, STAR 2.7.11a)    → BUILD  [StarIndex REUSE]
Step 3: CountMatrix      (DLPFC_001, GENCODE v44, q30, l20)   → BUILD
```

The original `quality_cutoff=20` entities remain in Hippo unchanged. Both parameter sets
coexist in the registry — Canon never overwrites results.

### 5.2 Upgrade a Tool Version

To re-run all samples with STAR 2.7.11b:

```bash
hippo entity create ToolVersion --name STAR --version 2.7.11b \
  --bioconda-build "2.7.11b--h9ee0642_0" --release-date 2024-02-01

for sample in DLPFC_001 DLPFC_002 DLPFC_003; do
  canon get CountMatrix \
    sample="ref:Sample{id=$sample}" \
    genome_build=GRCh38 gencode_version=44 \
    star_version=2.7.11b htseq_version=2.0.5 \
    cutadapt_version=4.6 quality_cutoff=20 min_length=20
done
```

Canon builds new `AlignmentFile` and `CountMatrix` entities for the new tool version while
leaving the original 2.7.11a results intact.

---

## Troubleshooting

**`EntityRefNotFound`:** A `ref:T{...}` expression matched no Hippo entities. Check that
the referenced entity exists with `hippo query <EntityType>`.

**`RuleNotFound`:** No rule in `canon_rules.yaml` produces the requested entity type with
the given parameters. Check the rule's `produces.match` keys against your `get` parameters.

**`MissingRequiredInput`:** A rule's `requires` block could not be satisfied. Run
`canon plan` to see which input step is failing and why.

**`CwltoolError`:** The CWL workflow failed during execution. Check the workflow run log
at `$work_dir/<run-id>/cwltool.log` and the WorkflowRun entity in Hippo for the failure
context.
