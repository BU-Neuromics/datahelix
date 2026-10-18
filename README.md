# DataHelix

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://datahelix-platform.github.io/datahelix/)

**Documentation site:** https://datahelix-platform.github.io/datahelix/

This repository hosts the DataHelix platform: documentation, cross-component integration tests, and submodules pointing at each component's standalone repository.

> ℹ️ **Mosaic (formerly Hippo, ADR-0004) and Aperture live in their own repos** ([datahelix-platform/mosaic](https://github.com/datahelix-platform/mosaic), [datahelix-platform/aperture](https://github.com/datahelix-platform/aperture)) and are mounted here as git submodules. Clone with `git clone --recurse-submodules`, or run `git submodule update --init` after a plain clone. Other components are expected to follow the same pattern over time.

## Components

| Component | Description | Source | Design Spec | User Docs |
|---|---|---|---|---|
| **Mosaic** | LinkML runtime — the platform's structured domain graph (metadata tracking is one application) | [datahelix-platform/mosaic](https://github.com/datahelix-platform/mosaic) (submodule) | [design/](mosaic/design/INDEX.md) | [docs/](mosaic/docs/introduction.md) |
| **Cappella** | Workflow engine | in-tree | [design/](cappella/design/INDEX.md) | [docs/](cappella/docs/introduction.md) |
| **Aperture** | AI-native data & workflow explorer (config-driven portal = substrate) | [datahelix-platform/aperture](https://github.com/datahelix-platform/aperture) (submodule) | [design/](aperture/design/INDEX.md) | — |
| **Bridge** | Integration middleware | in-tree | [design/](bridge/design/INDEX.md) | [docs/](bridge/docs/introduction.md) |
| **Reel** | AI-native data-story engine (headless; composes QuerySpec states into replayable stories) — turn path carried from Exon (Reel ADR-0008); harness migration outstanding; split from Aperture per [platform ADR-0003](platform/design/decisions/ADR-0003-reel-data-story-engine-separate-from-portal.md) | [datahelix-platform/reel](https://github.com/datahelix-platform/reel) (submodule: `reel/`) | [design/](https://github.com/datahelix-platform/reel/blob/main/design/INDEX.md) | — |

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

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

DataHelix is developed by Adam Labadorf with the National Center for PTSD Brain Bank, U.S. Department of Veterans Affairs.
