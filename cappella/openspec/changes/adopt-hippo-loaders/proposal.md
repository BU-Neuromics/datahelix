## Why

Cappella currently has its own `ExternalSourceAdapter` ABC, `CSVAdapter`, `JSONAdapter`, and `SQLAdapter` that duplicate field mapping and vocabulary normalization logic from Hippo. With the Unified Ingestion Framework (platform/design/sec4_unified_ingestion.md), Hippo now provides `EntityLoader` → `ConfigurableLoader` → `CSVLoader/JSONLoader/SQLLoader` in core. Cappella should subclass from Hippo rather than maintaining its own parallel implementations.

## What Changes

- **Modified** `ExternalSourceAdapter` — subclasses `hippo.core.loaders.EntityLoader` instead of its own ABC
- **Modified** `CSVAdapter` — subclasses `hippo.core.loaders.CSVLoader`, adds Cappella-specific transport (HTTP polling, manual_upload source)
- **Modified** `JSONAdapter` — subclasses `hippo.core.loaders.JSONLoader`
- **Modified** `SQLAdapter` — subclasses `hippo.core.loaders.SQLLoader`
- **Removed** duplicate field_map/vocabulary_map logic (inherited from `ConfigurableLoader`)
- **Modified** `IngestPipeline` — delegates to Hippo's `IngestPipeline` for the upsert loop

## Capabilities

### Modified Capabilities
- `external-source-adapter` — base class changes from local ABC to Hippo's EntityLoader

### New Capabilities
- (none — this is adoption of shared infrastructure)

## Impact

- **Code:** Modified 4 adapter files + pipeline; no new files
- **Dependencies:** Cappella now hard-depends on `hippo.core.loaders` (already depends on hippo)
- **Tests:** Existing Cappella adapter tests updated for new base class; new contract tests at monorepo root verify cross-component behavior
- **Risk:** Low — Cappella's existing tests define the expected behavior; refactoring internals while preserving external behavior
