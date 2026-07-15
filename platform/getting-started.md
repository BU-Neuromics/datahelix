# Getting Started with DataHelix

**Time:** ~30 minutes
**Goal:** Install the DataHelix platform, load sample data, run an RNA-seq artifact resolution, and query the results.

This guide walks through the full platform end-to-end: Mosaic (formerly Hippo, ADR-0004; metadata), Canon (artifact resolution), Cappella (ingestion), and Aperture (CLI). You only need to install the components relevant to your workflow — skip sections that don't apply.

---

## Before You Start

**Prerequisites:**
- Python 3.11 or later
- `pip` or `uv` (recommended)
- ~500 MB disk space
- Internet connection (for reference data download)

**What you'll build:**
A local DataHelix deployment with a small RNA-seq study dataset. You'll ingest sample metadata, register file locations, resolve canonical artifact paths, and query results via the CLI.

---

## Part 1: Install

### 1.1 Install Mosaic (required)

Mosaic is the metadata backbone — install it first.

```bash
pip install mosaic
# or with uv (faster)
uv pip install mosaic
```

Verify:

```bash
mosaic --version
# mosaic 0.4.0
```

### 1.2 Install Canon (if you work with file artifacts)

```bash
pip install canon
```

### 1.3 Install Cappella (if you ingest from external systems or run pipelines)

```bash
pip install cappella
```

### 1.4 Install Aperture CLI

```bash
pip install datahelix-aperture
```

Verify:

```bash
datahelix --version
# datahelix 0.4.0
```

---

## Part 2: Initialize a Project

Create a directory for your DataHelix deployment:

```bash
mkdir ~/my_study && cd ~/my_study
```

### 2.1 Initialize Mosaic

```bash
mosaic init --path .
```

This creates:
```
my_study/
├── mosaic.yaml          # Mosaic configuration
├── schema.yaml         # Entity type definitions (edit this for your data model)
└── mosaic.db            # SQLite database (created on first start)
```

### 2.2 Start the Mosaic REST API

```bash
mosaic serve &
```

Mosaic starts on `http://localhost:8001` by default. Check it's running:

```bash
curl http://localhost:8001/health
# {"status": "healthy", "version": "0.4.0"}
```

---

## Part 3: Define Your Schema

Edit `schema.yaml` to define your entity types. Here's a minimal RNA-seq study schema:

```yaml
# schema.yaml

entities:
  Subject:
    description: "Research subject (donor)"
    fields:
      subject_id:
        type: string
        required: true
        unique: true
        indexed: true
      species:
        type: string
        enum: [Homo sapiens, Mus musculus]
        required: true
      age_at_collection:
        type: integer

  Sample:
    description: "Biological sample"
    fields:
      sample_id:
        type: string
        required: true
        unique: true
        indexed: true
      tissue_type:
        type: string
        required: true
      subject:
        type: ref
        target: Subject
        required: true

  Datafile:
    description: "Raw or processed file"
    fields:
      file_path:
        type: string
        required: true
      file_type:
        type: string
        enum: [fastq, bam, bigwig, counts_matrix]
        required: true
      sample:
        type: ref
        target: Sample
```

Apply the schema:

```bash
mosaic migrate
# Schema migration complete. 3 entity types created.
```

---

## Part 4: Ingest Data

### 4.1 Create a sample data file

Create `data/subjects.json`:

```json
[
  {"subject_id": "SUBJ-001", "species": "Homo sapiens", "age_at_collection": 42},
  {"subject_id": "SUBJ-002", "species": "Homo sapiens", "age_at_collection": 38}
]
```

Create `data/samples.json`:

```json
[
  {"sample_id": "SAMP-001", "tissue_type": "prefrontal cortex", "subject": {"external_id": "SUBJ-001"}},
  {"sample_id": "SAMP-002", "tissue_type": "hippocampus", "subject": {"external_id": "SUBJ-002"}}
]
```

Create `data/datafiles.json`:

```json
[
  {"file_path": "/data/raw/SAMP-001.R1.fastq.gz", "file_type": "fastq", "sample": {"external_id": "SAMP-001"}},
  {"file_path": "/data/raw/SAMP-001.R2.fastq.gz", "file_type": "fastq", "sample": {"external_id": "SAMP-001"}},
  {"file_path": "/data/raw/SAMP-002.R1.fastq.gz", "file_type": "fastq", "sample": {"external_id": "SAMP-002"}},
  {"file_path": "/data/raw/SAMP-002.R2.fastq.gz", "file_type": "fastq", "sample": {"external_id": "SAMP-002"}}
]
```

### 4.2 Ingest via CLI

```bash
mosaic ingest data/subjects.json --entity-type Subject
# Ingested 2 Subject entities (2 created, 0 updated, 0 unchanged)

mosaic ingest data/samples.json --entity-type Sample
# Ingested 2 Sample entities (2 created, 0 updated, 0 unchanged)

mosaic ingest data/datafiles.json --entity-type Datafile
# Ingested 4 Datafile entities (4 created, 0 updated, 0 unchanged)
```

---

## Part 5: Query with Aperture CLI

### 5.1 Configure `datahelix`

```bash
datahelix config set mosaic.url http://localhost:8001
```

### 5.2 List entities

```bash
datahelix list Subject
```

Output:

```
ID                                    subject_id   species         age_at_collection
────────────────────────────────────  ───────────  ──────────────  ─────────────────
3f4a8b12-...                          SUBJ-001     Homo sapiens    42
7c1d9e34-...                          SUBJ-002     Homo sapiens    38
```

### 5.3 Filter entities

```bash
datahelix list Sample --filter tissue_type="prefrontal cortex"
```

### 5.4 Get provenance for a specific entity

```bash
datahelix history SAMP-001 --entity-type Sample
```

Output:

```
Version  Actor    Operation  Changed fields        Timestamp
───────  ───────  ─────────  ────────────────────  ────────────────────
1        system   create     subject, tissue_type  2026-10-15T09:12:33Z
```

---

## Part 6: Resolve Artifacts with Canon

Canon resolves where canonical output files live, given a set of input entities.

### 6.1 Initialize Canon

```bash
canon init --path .
```

This creates `canon.yaml` for your Canon rules configuration.

### 6.2 Define a resolution rule

Edit `canon.yaml` to add a rule that resolves aligned BAM files for samples:

```yaml
# canon.yaml

rules:
  - name: aligned_bam
    description: "Aligned BAM from RNA-seq"
    entity_type: Sample
    output_type: bam
    path_template: "/data/aligned/{sample.sample_id}.Aligned.sortedByCoord.out.bam"
    requires:
      - entity_field: sample_id
```

### 6.3 Resolve an artifact

```bash
canon resolve --entity-type Sample --entity-id SAMP-001 --rule aligned_bam
```

Output:

```
Rule:    aligned_bam
Entity:  Sample SAMP-001
Path:    /data/aligned/SAMP-001.Aligned.sortedByCoord.out.bam
Status:  found
Size:    2.3 GB
```

Canon checks whether the file exists at the resolved path and reports its status.

### 6.4 Batch resolve for a collection

```bash
datahelix list Sample --format json | canon resolve --rule aligned_bam --from-stdin
```

This resolves artifacts for all samples and reports which are present, missing, or stale.

---

## Part 7: Run a Pipeline with Cappella

Cappella orchestrates data ingestion from external sources and pipeline execution.

### 7.1 Configure Cappella

```bash
cappella init --path .
```

Edit `cappella.yaml` to add a CSV ingestion source:

```yaml
# cappella.yaml

adapters:
  - name: sample_manifest
    type: csv
    source_path: /data/incoming/manifest.csv
    entity_type: Sample
    field_mapping:
      sample_id: "SampleID"
      tissue_type: "Tissue"
      subject: "DonorID"   # resolves via ExternalID to Subject entity

triggers:
  - name: ingest_new_manifest
    source:
      type: manual
      api_path: /sync/manifest
    action:
      type: adapter_sync
      adapter: sample_manifest
```

### 7.2 Run the ingestion manually

```bash
cappella sync manifest
```

Cappella reads the CSV, maps fields to Mosaic schema, and upserts entities. Existing
entities with matching `sample_id` are updated only if fields changed; unchanged
entities are skipped.

---

## Part 8: Check System Status

```bash
datahelix status
```

Output:

```
Component   Status    URL                      Version
──────────  ────────  ───────────────────────  ───────
mosaic       ✓ online  http://localhost:8001    0.4.0
canon       ✓ online  (SDK mode)              0.3.0
cappella    ✓ online  http://localhost:8002    0.2.0
```

---

## What's Next

- **Multi-user deployment:** Add Bridge for API key authentication. See
  [`platform/deployment.md`](deployment.md) for Docker Compose setup.

- **Reference data:** Load gene annotations and ontology terms with
  `mosaic reference install ensembl` and `mosaic reference install fma`.

- **Custom schema:** Add more entity types, define relationships, and set up validators.
  See the [Mosaic schema guide](../mosaic/docs/schema-guide.md).

- **Trigger automation:** Configure Cappella to auto-sync from STARLIMS, REDCap, or
  webhook sources. See the [Cappella user guide](../cappella/docs/user_guide.md).

- **Python SDK:** Use `MosaicClient` directly in notebooks for custom analysis.
  See the [Mosaic API reference](../mosaic/docs/api-reference.md).

---

## Troubleshooting

**`mosaic serve` fails to start:**
Check that port 8001 is not already in use: `lsof -i :8001`. Change the port in
`mosaic.yaml` (`server.port: 8002`) if needed.

**`datahelix list` shows "connection refused":**
Make sure Mosaic is running: `mosaic serve &`. Verify the URL in `~/.config/datahelix/aperture.yaml`
or run `datahelix config show`.

**Schema migration fails:**
If you changed an existing field type, Mosaic will refuse the migration to protect data
integrity. Create a new field and use `mosaic migrate --allow-column-add` for additive
changes only.

**"entity_type not found" on ingest:**
Run `mosaic migrate` first to apply your schema.yaml changes before ingesting.
