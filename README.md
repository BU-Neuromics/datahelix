# drylims — Bioinformatics Analysis Software System

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://va-ncptsdbb-bioinformatics.github.io/drylims/)

**Documentation site:** https://va-ncptsdbb-bioinformatics.github.io/drylims/

This repository hosts the BASS platform: documentation, cross-component integration tests, and submodules pointing at each component's standalone repository.

> ℹ️ **Hippo and Aperture live in their own repos** ([BU-Neuromics/hippo](https://github.com/BU-Neuromics/hippo), [BU-Neuromics/aperture](https://github.com/BU-Neuromics/aperture)) and are mounted here as git submodules. Clone with `git clone --recurse-submodules`, or run `git submodule update --init` after a plain clone. Other components are expected to follow the same pattern over time.

## Components

| Component | Description | Source | Design Spec | User Docs |
|---|---|---|---|---|
| **Hippo** | LinkML runtime — the platform's structured domain graph (metadata tracking is one application) | [BU-Neuromics/hippo](https://github.com/BU-Neuromics/hippo) (submodule) | [design/](hippo/design/INDEX.md) | [docs/](hippo/docs/introduction.md) |
| **Cappella** | Workflow engine | in-tree | [design/](cappella/design/INDEX.md) | [docs/](cappella/docs/introduction.md) |
| **Aperture** | AI-native data & workflow explorer (config-driven portal = substrate) | [BU-Neuromics/aperture](https://github.com/BU-Neuromics/aperture) (submodule) | [design/](aperture/design/INDEX.md) | — |
| **Bridge** | Integration middleware | in-tree | [design/](bridge/design/INDEX.md) | [docs/](bridge/docs/introduction.md) |

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
