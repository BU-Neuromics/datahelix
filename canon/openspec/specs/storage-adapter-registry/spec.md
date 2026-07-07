# Storage Adapter Registry Specification

## Requirements

### Requirement: StorageAdapterRegistry discovers adapters via entry points

The system SHALL provide a `StorageAdapterRegistry` class in `canon/storage/registry.py` that discovers and instantiates `StorageAdapter` implementations via the `canon.storage_adapters` entry point group at startup.

#### Scenario: Registry loads bundled LocalStorageAdapter
- **WHEN** `StorageAdapterRegistry.load_from_entry_points()` is called with a `CanonConfig` that has `output_storage.type = "local"`
- **THEN** the registry SHALL contain a `LocalStorageAdapter` instance mapped to URI schemes `["file", ""]`

#### Scenario: Registry raises CanonConfigError for unknown storage type
- **WHEN** a `CanonConfig` specifies `output_storage.type = "gcs"` but no `canon-storage-gcs` package is installed
- **THEN** a `CanonConfigError` SHALL be raised with a message listing available adapter names

### Requirement: StorageAdapterRegistry routes URIs by scheme

The registry SHALL provide an `adapter_for_uri(uri)` method that returns the appropriate `StorageAdapter` based on the URI scheme prefix (e.g., `s3://` → S3 adapter, `file://` → local adapter).

#### Scenario: adapter_for_uri resolves file:// to LocalStorageAdapter
- **WHEN** `adapter_for_uri("file:///data/output.bam")` is called
- **THEN** the returned adapter SHALL be the `LocalStorageAdapter` instance

#### Scenario: adapter_for_uri resolves bare path to LocalStorageAdapter
- **WHEN** `adapter_for_uri("/data/output.bam")` is called (no scheme prefix)
- **THEN** the returned adapter SHALL be the `LocalStorageAdapter` instance (empty string scheme)

#### Scenario: adapter_for_uri raises CanonConfigError for unregistered scheme
- **WHEN** `adapter_for_uri("s3://bucket/key")` is called and no S3 adapter is registered
- **THEN** a `CanonConfigError` SHALL be raised with a descriptive message

### Requirement: StorageAdapterRegistry provides default_adapter

The registry SHALL provide a `default_adapter` property that returns the adapter configured in `output_storage.type` in the `CanonConfig`. This is used by `OutputIngestionPipeline` for output relocation when the destination URI is constructed (not yet known to have a scheme).

#### Scenario: default_adapter returns the configured adapter
- **WHEN** `output_storage.type = "local"` in config
- **THEN** `registry.default_adapter` SHALL return the `LocalStorageAdapter` instance
