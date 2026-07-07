# Storage Adapter Abc Specification

## Requirements

### Requirement: StorageAdapter ABC defines the storage contract

The system SHALL provide a `StorageAdapter` abstract base class in `canon/storage/base.py` that defines the behavioral contract for all storage backends. The ABC SHALL declare abstract methods `put()`, `get()`, and `exists()`, plus a non-abstract `build_dest_uri()` with a default `NotImplementedError` implementation.

#### Scenario: put() relocates a local file to permanent storage
- **WHEN** `put(local_path, dest_uri)` is called with a valid local file path and destination URI
- **THEN** the file SHALL be copied/uploaded to the destination and the method SHALL return the canonical URI of the relocated file

#### Scenario: put() raises CanonStorageError on failure
- **WHEN** `put()` is called and the storage backend encounters an error (e.g., permission denied, disk full)
- **THEN** the method SHALL raise `CanonStorageError` with a descriptive message

#### Scenario: get() stages a remote file to a local directory
- **WHEN** `get(uri, local_dir)` is called with a valid URI and local directory path
- **THEN** the file SHALL be made available in `local_dir` and the method SHALL return the local `Path` to the staged file

#### Scenario: get() raises CanonStorageError on failure
- **WHEN** `get()` is called and the file cannot be staged (e.g., URI not found, network error)
- **THEN** the method SHALL raise `CanonStorageError`

#### Scenario: exists() checks URI accessibility
- **WHEN** `exists(uri)` is called with a URI
- **THEN** the method SHALL return `True` if the file is accessible, `False` otherwise, without raising exceptions

### Requirement: StorageAdapter declares name and uri_schemes

Each `StorageAdapter` subclass SHALL declare a `name` class attribute (str) and a `uri_schemes` class attribute (list of str) identifying which URI schemes it handles.

#### Scenario: Adapter exposes name and uri_schemes
- **WHEN** a `StorageAdapter` subclass is instantiated
- **THEN** `adapter.name` SHALL return the entry point name (e.g., `"local"`) and `adapter.uri_schemes` SHALL return the list of URI schemes it handles (e.g., `["file", ""]`)

### Requirement: CanonStorageError exception class

The system SHALL define a `CanonStorageError` exception class in `canon/storage/base.py` (or `canon/exceptions.py`) for all storage-related failures. It SHALL be a subclass of `CanonError`.

#### Scenario: CanonStorageError is raised by storage operations
- **WHEN** a storage operation fails
- **THEN** a `CanonStorageError` SHALL be raised with a human-readable message describing the failure
