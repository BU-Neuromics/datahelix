# BASS — Bioinformatics Analysis Software System

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://va-ncptsdbb-bioinformatics.github.io/drylims-docs/)

**Documentation site:** https://va-ncptsdbb-bioinformatics.github.io/drylims-docs/

This repository contains all documentation for the BASS platform and its components.

## Components

| Component | Description | Design Spec | User Docs |
|---|---|---|---|
| **Hippo** | Metadata tracking service | [design/](hippo/design/INDEX.md) | [docs/](hippo/docs/introduction.md) |
| **Cappella** | Workflow engine | [design/](cappella/design/INDEX.md) | [docs/](cappella/docs/introduction.md) |
| **Aperture** | Interface layer | [design/](aperture/design/INDEX.md) | [docs/](aperture/docs/introduction.md) |
| **Bridge** | Integration middleware | [design/](bridge/design/INDEX.md) | [docs/](bridge/docs/introduction.md) |

## Platform Documentation

- [Platform Overview](platform/overview.md)
- [System Architecture](platform/architecture.md)
- [Glossary](platform/glossary.md)
- [Deployment Guide](platform/deployment.md)

## Repository Structure

```
<component>/
├── design/     # Engineering specification — internal reference
│   └── INDEX.md
└── docs/       # User-facing documentation
```

Design specs are structured engineering documents intended for developers building and maintaining each component. User docs are intended for developers and researchers using the components.
