## ADDED Requirements

### Requirement: HttpsStorageAdapter downloads files from HTTP/HTTPS URIs

The system SHALL provide a `HttpsStorageAdapter` in `canon/storage/https.py` implementing `StorageAdapter` with `name = "https"` and `uri_schemes = ["https", "http"]`. It SHALL be read-only: `get()` and `exists()` are implemented; `put()` and `build_dest_uri()` SHALL raise `CanonStorageError` with a message indicating HTTPS is a read-only source.

#### Scenario: get() streams file to local_dir
- **WHEN** `get(uri, local_dir)` is called with a valid HTTPS URI
- **THEN** the file SHALL be downloaded via httpx streaming, written to `local_dir/<filename>`, and the local `Path` SHALL be returned

#### Scenario: get() raises CanonStorageError on HTTP error
- **WHEN** `get()` receives a non-2xx HTTP response (404, 403, 500, etc.)
- **THEN** a `CanonStorageError` SHALL be raised with the HTTP status code in the message

#### Scenario: get() raises CanonStorageError on network failure
- **WHEN** `get()` cannot connect to the server (timeout, DNS failure, etc.)
- **THEN** a `CanonStorageError` SHALL be raised wrapping the underlying exception

#### Scenario: exists() returns True for accessible URI
- **WHEN** `exists(uri)` is called and the server returns 2xx to a HEAD request
- **THEN** the method SHALL return `True`

#### Scenario: exists() returns False for inaccessible URI
- **WHEN** `exists(uri)` is called and the server returns 404 or the host is unreachable
- **THEN** the method SHALL return `False` without raising

#### Scenario: put() raises CanonStorageError
- **WHEN** `put(local_path, dest_uri)` is called on HttpsStorageAdapter
- **THEN** a `CanonStorageError` SHALL be raised with message "HTTPS adapter is read-only"

#### Scenario: filename derived from URI path
- **WHEN** `get("https://example.com/data/genome.fa.gz", local_dir)` is called
- **THEN** the downloaded file SHALL be written to `local_dir/genome.fa.gz`

### Requirement: HttpsStorageAdapter registered via entry points

The `HttpsStorageAdapter` SHALL be registered in `pyproject.toml` under `canon.storage_adapters` with names `https` and `http`.

#### Scenario: Entry point discovery finds HttpsStorageAdapter for both schemes
- **WHEN** `StorageAdapterRegistry.adapter_for_uri("https://example.com/file.fa")` is called
- **THEN** the returned adapter SHALL be `HttpsStorageAdapter`
