# Canon — Semantic Artifact Resolver

!!! warning "Not Yet Implemented"
    Canon is in the design specification phase. The rules DSL and resolution algorithm are fully specified; executor and storage adapter plugins are designed but not yet implemented.

Canon is the **artifact resolver** for the BASS platform. It answers one question: *does this computational result already exist, and if not, how do I produce it?*

Artifacts are identified by their **semantic identity** — entity type, sample, reference genome, tool version, and parameters — not by file path. Two results produced from the same inputs with the same tool are the same artifact, regardless of when or where they were produced.

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

## Related Components

- [Hippo](../hippo/index.md) — Canon resolves entity metadata from Hippo to parameterize artifact rules
- [Cappella](../cappella/index.md) — Calls `canon.resolve()` during collection assembly
- [Aperture](../aperture/index.md) — Users can inspect artifact status via the CLI
- [Bridge](../bridge/index.md) — Authentication for multi-user Canon deployments

## User Documentation

- [Introduction](user-docs/introduction.md) — Detailed overview
- [Quick Start](user-docs/quickstart.md) — Get started with Canon
- [User Guide](user-docs/user-guide.md) — Complete usage guide

## Design Specification

- [Overview & Scope](design/sec1_overview.md)
- [Architecture](design/sec2_architecture.md)
- [Rules DSL](design/sec3_rules_dsl.md)
- [CWL Integration](design/sec3b_cwl_integration.md)
- [Resolution Algorithm](design/sec4_resolution_algorithm.md)
- [Executor Adapters](design/sec5_executor_adapters.md)
- [Storage Adapters](design/sec5b_storage_adapters.md)
- [Hippo Integration](design/sec6_hippo_integration.md)
- [Non-Functional Requirements](design/sec7_nfr.md)
- [Dynamic Rules](design/sec8_dynamic_rules.md)
- [Appendix A: RNA-seq Example](design/appendix_a_rnaseq_example.md)
- [Reference: canon.yaml Config](design/reference_canon_yaml.md)
- [Reference: canon-rules.yaml](design/reference_canon_rules_yaml.md)
