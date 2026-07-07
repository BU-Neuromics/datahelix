# Local Storage Adapter Specification

## Requirements

### Requirement: LocalStorageAdapter implements StorageAdapter for filesystem storage

The system SHALL provide a `LocalStorageAdapter` class in `canon/storage/local.py` that implements `StorageAdapter` for local filesystem and NFS/shared filesystem storage. It SHALL have `name = "local"` and `uri_schemes = ["file", ""]`.

#### Scenario: put() copies file to destination and returns file:// URI
- **WHEN** `put(local_path, dest_uri)` is called with a valid local file
- **THEN** the file SHALL be copied to the destination path (creating parent directories as needed) and the method SHALL return a `file://` prefixed URI

#### Scenario: put() raises CanonStorageError when source file missing
- **WHEN** `put()` is called with a `local_path` that does not exist
- **THEN** a `CanonStorageError` SHALL be raised

#### Scenario: get() returns existing path as-is when file is accessible
- **WHEN** `get(uri, local_dir)` is called and the URI resolves to a path that already exists on the filesystem
- **THEN** the method SHALL return the resolved `Path` directly without copying (no-op for shared filesystems)

#### Scenario: get() copies file to local_dir when source path not locally accessible
- **WHEN** `get(uri, local_dir)` is called and the file exists at the URI path but is not in `local_dir`
- **THEN** the method SHALL copy the file to `local_dir` and return the local copy path

#### Scenario: get() raises CanonStorageError when URI path does not exist
- **WHEN** `get()` is called with a URI whose resolved path does not exist
- **THEN** a `CanonStorageError` SHALL be raised

#### Scenario: exists() checks filesystem path existence
- **WHEN** `exists(uri)` is called
- **THEN** the method SHALL return `True` if the path exists on the filesystem, `False` otherwise

#### Scenario: exists() handles both file:// and bare paths
- **WHEN** `exists()` is called with `file:///data/output.bam` or `/data/output.bam`
- **THEN** both SHALL resolve to the same filesystem path and return the same result

### Requirement: LocalStorageAdapter constructs destination URIs from base_path

The `LocalStorageAdapter` SHALL accept a `base_path` configuration parameter. `build_dest_uri()` SHALL construct URIs as `file://<base_path>/<entity_type_lower>/<entity_id>/<filename>`.

#### Scenario: build_dest_uri creates structured path
- **WHEN** `build_dest_uri("AlignmentFile", "abc-123", "output.bam")` is called
- **THEN** the result SHALL be `file://<base_path>/alignmentfile/abc-123/output.bam`

### Requirement: LocalStorageAdapter is registered via entry point

The `LocalStorageAdapter` SHALL be registered in `pyproject.toml` under the `canon.storage_adapters` entry point group with the name `local`.

#### Scenario: Entry point discovery finds LocalStorageAdapter
- **WHEN** `importlib.metadata.entry_points(group="canon.storage_adapters")` is called
- **THEN** the result SHALL include an entry with `name="local"` that loads `LocalStorageAdapter`
