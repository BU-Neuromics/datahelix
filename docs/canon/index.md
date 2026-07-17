# Canon — Semantic Artifact Resolver

!!! warning "Not Yet Implemented"
    Canon is in the design specification phase. The rules DSL and resolution algorithm are fully specified; executor and storage adapter plugins are designed but not yet implemented.

Canon is the **artifact resolver** for the DataHelix platform. It answers one question: *does this computational result already exist, and if not, how do I produce it?*

Artifacts are identified by their **semantic identity** — entity type, sample, reference genome, tool version, and parameters — not by file path. Two results produced from the same inputs with the same tool are the same artifact, regardless of when or where they were produced.

## Who Is Canon For?

- **Bioinformaticians** who run analysis pipelines and want to avoid recomputing results that already exist
- **Pipeline authors** who need a declarative way to define how artifacts are produced and what inputs they require
- **Lab teams** who share computed results across projects and want a registry of what has been produced, with what parameters

## When to Use Canon

Use Canon when you need to:

- **Avoid redundant computation** — Before running an expensive alignment or analysis, check whether the result already exists with the same parameters
- **Track artifact provenance** — Know exactly which tool version, genome build, and parameters produced a given file
- **Share results across projects** — A BAM file produced for one project can be reused by any other project with matching parameters
- **Define reproducible pipelines** — Declarative YAML rules specify inputs, tools, and CWL workflows; Canon handles resolution and execution

Canon is **not** a replacement for Snakemake or Nextflow. It is a registry-lookup layer that runs *before* execution — checking whether the result exists in Hippo before invoking a CWL workflow to produce it.

## Key Features

- **Semantic deduplication** — Avoid recomputing results that already exist
- **Rules DSL** — Declarative YAML rules define how artifacts are produced and what inputs they require
- **Executor adapters** — Run computations locally, on HPC clusters, or in the cloud
- **Storage adapters** — Locate and stage artifacts across filesystems and object stores
- **CWL integration** — Common Workflow Language (v1.2) for portable workflow definitions
- **Hippo integration** — Resolve sample metadata and register produced artifacts back into the entity store

!!! warning "Not Yet Implemented"
    The following features are planned for v0.2+ and are not yet available:

    - **Storage adapters** — S3, GCS, OSF, and iRODS backends (local filesystem only in v0.1)
    - **Dynamic rule registration** — Runtime rule loading and convention-based output mapping
    - **Non-cwltool executors** — Toil, Nextflow, and other executor plugins

## Key Concepts

| Concept | Description |
|---|---|
| **Semantic identity** | An artifact is identified by its parameters (sample, genome build, tool version, etc.) — not its file path. Same parameters = same artifact. |
| **Rule** | A YAML declaration that defines how to produce an artifact: what inputs it requires, what tool and CWL workflow to run, and what outputs it produces. |
| **Resolution** | The process of checking Hippo for an existing artifact matching a specification, and producing it if not found. Outcomes: `REUSE`, `BUILD`, `FETCH`, or `FAIL`. |
| **Entity reference** | A parameter that points to a Hippo entity (e.g., `genome_build=ref:GenomeBuild{name=GRCh38}`), enabling graph traversal queries across artifacts. |
| **Artifact spec** | A request for a specific artifact: entity type + parameter set. Canon resolves it to a URI or triggers production. |
| **WorkflowRun** | A record of a CWL execution, linking inputs, outputs, tool version, and timing back to Hippo for provenance. |

## Architecture Overview

Canon sits between Cappella (which requests file resolution) and the CWL execution layer:

```
Traditional:  User → Snakemake → runs pipeline → produces file
Canon:        User → Canon → checks Hippo → already exists? → return URI
                                           → not found? → CWL → execute → ingest → return URI
```

All produced artifacts are registered as Hippo entities with full provenance. Canon delegates execution to the configured CWL runner (cwltool for local, Toil or Nextflow for HPC/cloud).

## Getting Started

```bash
pip install canon
canon plan my-artifact-spec.yaml   # dry-run: show what would be built
canon get my-artifact-spec.yaml    # resolve: reuse or build
```

See the **[Quick Start guide](docs/quickstart.md)** for a complete walkthrough — from rule definition through artifact resolution and provenance inspection.

## Related Components

- [Mosaic](../mosaic/index.md) — Canon resolves entity metadata from Hippo to parameterize artifact rules
- [Cappella](../cappella/index.md) — Calls `canon.resolve()` during collection assembly
- [Aperture](../aperture/index.md) — Users can inspect artifact status via the CLI
- [Bridge](../bridge/index.md) — Authentication for multi-user Canon deployments

## User Documentation

- [Introduction](docs/introduction.md) — Detailed overview
- [Quick Start](docs/quickstart.md) — Get started with Canon
- [User Guide](docs/user-guide.md) — Complete usage guide

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [Rules DSL](design/sec3_rules_dsl.md)
- [CWL Integration](design/sec3b_cwl_integration.md)
- [Resolution Algorithm](design/sec4_resolution_algorithm.md)
- [Executor Adapters](design/sec5_executor_adapters.md)
- [Storage Adapters](design/sec5b_storage_adapters.md)
- [Mosaic Integration](design/sec6_mosaic_integration.md)
- [Non-Functional Requirements](design/sec7_nfr.md)
- [Dynamic Rules](design/sec8_dynamic_rules.md)
- [Appendix A: RNA-seq Example](design/appendix_a_rnaseq_example.md)
- [Reference: canon.yaml Config](design/reference_canon_yaml.md)
- [Reference: canon-rules.yaml](design/reference_canon_rules_yaml.md)
