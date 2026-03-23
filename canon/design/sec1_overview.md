## 1. Overview & Scope

**Document status:** Draft v0.1  
**Depends on:** platform/design/INDEX.md

---

### 1.1 What Is Canon?

Canon is an open-source **semantic artifact resolver** for computational research pipelines.
It provides a single, composable operation:

> *Given a specification for a computational artifact, find it in the registry or produce it.*

A "specification" is an entity type and a set of metadata parameters — not a file path. For
example: "an RNA-seq alignment of sample AD001 against GRCh38 using STAR." Canon checks whether
a Hippo entity matching that specification already exists. If it does, Canon returns its URI.
If it does not, Canon finds a rule that can produce it, resolves that rule's inputs the same way
(recursively), runs the appropriate CWL workflow, and ingests the result back into Hippo.

Canon is deliberately narrow. It does not manage cohorts, schedule batch jobs, or orchestrate
multi-sample analyses. Those concerns belong to Cappella. Canon answers one question at a time
about one artifact at a time — and answers it well.

---

### 1.2 The Problem Canon Solves

Computational research produces enormous quantities of intermediate files: trimmed FASTQs,
aligned BAMs, gene count matrices, differential expression results. These files are expensive
to produce — in compute time, storage, and researcher effort. Yet they are routinely reproduced
from scratch because:

- There is no shared registry of what has already been computed and with what parameters
- File paths are local, fragile, and carry no semantic information about how they were produced
- Tools like Snakemake and Nextflow manage local caches but have no cross-project, cross-lab,
  or cross-time awareness

Canon solves this by making **artifact identity semantic rather than path-based**. A BAM file's
identity is its parameter set — the sample, the reference genome, the aligner, the key
parameters. Two BAMs produced with the same parameters from the same sample are the same
artifact, regardless of where they live on disk or when they were produced.

Because Canon stores all produced artifacts as Hippo entities, the registry spans projects,
datasets, time, and (eventually) institutions. Before running any computation, Canon checks
whether the result already exists. Compute is only performed when genuinely necessary.

---

### 1.3 Relationship to Snakemake and Nextflow

Canon is not a replacement for Snakemake or Nextflow. It is a layer above them.

Snakemake and Nextflow are execution engines — they manage job scheduling, HPC submission,
container execution, retry logic, and file staging. They are mature, well-tested, and
widely adopted. Canon does not reimplement any of this.

Canon's contribution is the **registry lookup layer** that runs before execution:

```
Traditional:  User → Snakemake → runs pipeline → produces file
Canon:        User → Canon → checks Hippo → already exists? return URI
                                           → not found? → CWL → Snakemake/cwltool → produce → ingest → return URI
```

Canon uses **CWL (Common Workflow Language)** as its workflow description format. CWL is a
schematic, executor-agnostic DAG specification — it describes what a workflow does without
specifying how it runs. CWL workflows can be executed by multiple backends: cwltool (local),
Toil (HPC/cloud), Nextflow (CWL mode), Seven Bridges, Terra, and others. Canon delegates
all execution to the configured CWL runner.

---

### 1.4 Position in the BASS Platform

Canon is the third independently deliverable module of the BASS platform, after Hippo (metadata
tracking) and Cappella (integration and harmonization).

```
┌─────────────────────────────────────────────────────────────────┐
│                         BASS Platform                            │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │  Hippo   │◄───│    Canon     │    │      Cappella        │   │
│  │  (MTS)   │    │  (Resolver)  │◄───│  (Orchestrator)      │   │
│  └──────────┘    └──────┬───────┘    └──────────────────────┘   │
│       ▲                 │                                        │
│       │           ┌─────▼──────┐                                 │
│       │           │ CWL Runner │                                 │
│       │           │(cwltool,   │                                 │
│       └───────────│ Toil, etc) │                                 │
│    (ingest)       └────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Dependencies:**
- Canon **requires** Hippo — it reads the artifact registry and writes results back
- Canon **does not require** Cappella — it can be used standalone from the command line
- Cappella **calls Canon** — it resolves which artifacts to request and passes individual
  specifications to Canon one at a time

**Data flow:**
1. Cappella (or a researcher directly) calls `canon get` with a spec
2. Canon queries Hippo: does an entity matching this spec exist?
3. If yes: Canon returns the entity's URI. Done.
4. If no: Canon finds the matching CWL workflow, resolves its inputs recursively (step 2–4
   for each required input), runs the workflow via the CWL executor, ingests the output
   entity into Hippo, returns the URI.
5. All produced entities are queryable in Hippo with full provenance.

---

### 1.5 Non-Goals

Canon explicitly does not:

- **Manage cohorts or sample sets** — deciding which samples to process is Cappella's job
- **Schedule or parallelize batch runs** — Canon resolves one artifact at a time; Cappella
  calls Canon in parallel if needed
- **Implement execution** — Canon delegates entirely to CWL runners (cwltool, Toil, etc.)
- **Store data** — all persistent state lives in Hippo; Canon is stateless
- **Provide a REST API** — Canon is a CLI tool and Python library; transport layers are future
- **Replace Snakemake or Nextflow** — Canon wraps them via CWL; existing pipelines continue
  to work unchanged
- **Handle authentication or access control** — inherited from Hippo's token auth

---

### 1.6 Delivery Scope (v0.1)

**In scope:**
- Canon rules registry (`canon_rules.yaml`) — mapping from artifact spec to CWL workflow
- Hippo registry lookup — exact-match query before any execution
- Lazy recursive dependency resolution — walk rule graph on demand
- CWL execution via `cwltool` (local) and `ContainerExecutor` (Docker/Singularity)
- Output ingestion — ingest CWL outputs as Hippo entities with `WorkflowRun` provenance
- CLI: `canon get`, `canon plan` (dry run), `canon rules list/validate`
- Cycle detection — `CanonCycleError` with cycle path on circular rule dependencies

**Explicitly out of scope for v0.1:**
- Partial specification / constraint queries (v0.2) — exact match only
- Aggregate/collect rules for sample-set outputs like counts matrices (v0.2)
- Snakemake and Nextflow native adapters (v0.2)
- DRS server / cross-lab federation (v0.3)
- Visual workflow builder (future)
- REST API (future)
- Authentication beyond Hippo bearer token (future)

---

### 1.7 Key Design Principles

| Principle | Description |
|---|---|
| **One operation** | Canon does one thing: `get(spec) → URI`. Everything else is composition of this. |
| **Semantic identity** | Artifact identity is parameter-based, not path-based. Two artifacts with the same parameters are the same artifact. |
| **Registry-first** | Always check Hippo before running anything. Compute only what does not already exist. |
| **Lazy resolution** | Resolve dependencies on demand, not upfront. Walk the rule graph one step at a time. |
| **Delegate execution** | Canon never runs commands. CWL runners handle all execution details. |
| **Stateless** | Canon owns no persistent state. Hippo is the record of truth. Canon's ephemeral run state (in-flight jobs) is rebuildable from Hippo. |
| **CWL-native** | Workflow descriptions are standard CWL. Canon adds only a thin metadata annotation layer for Hippo entity mapping. |
| **Composable** | Canon can be used standalone (CLI), embedded in Python, or called by Cappella. The interface is the same in all cases. |

---

### 1.8 Glossary

| Term | Definition |
|---|---|
| **Artifact** | Any computational output tracked by Canon — a file, a metadata record, a derived result. Represented as a Hippo entity with a URI. |
| **Spec** | A specification for an artifact: entity type + metadata parameter set. `AlignmentFile{genome_build=GRCh38, aligner=STAR, sample_id=AD001}`. |
| **Canon rule** | A rule declaring how to produce an artifact of a given type from required inputs, using a specified CWL workflow. |
| **Resolution** | The process of finding or producing an artifact matching a spec. REUSE if found in Hippo; BUILD if not. |
| **REUSE** | A resolution decision where a matching artifact already exists in Hippo. No computation performed. |
| **BUILD** | A resolution decision where no matching artifact exists. Canon runs the CWL workflow to produce it. |
| **CWL** | Common Workflow Language — a standard, executor-agnostic format for describing computational workflows as DAGs. |
| **CWL runner** | A tool that executes CWL workflows: cwltool (local), Toil (HPC/cloud), Nextflow CWL mode, etc. |
| **WorkflowRun** | A Hippo entity recording the execution of a Canon rule: inputs, parameters, executor, status, outputs. |
| **Provenance metadata** | The full set of parameters used to produce an artifact, stored as fields on the Hippo entity. Enables future queries like "all GRCh38/STAR alignments of DLPFC samples." |
