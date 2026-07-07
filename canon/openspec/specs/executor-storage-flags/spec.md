# Executor Storage Flags Specification

## Requirements

### Requirement: CWLExecutorAdapter declares staging requirements

The `CWLExecutorAdapter` ABC SHALL declare two boolean class attributes: `requires_local_staging` (default `True`) and `requires_output_relocation` (default `True`). These flags tell Canon whether the executor needs Canon to handle file staging for inputs and output relocation for outputs.

#### Scenario: CwltoolAdapter requires both staging and relocation
- **WHEN** a `CwltoolAdapter` instance is inspected
- **THEN** `requires_local_staging` SHALL be `True` and `requires_output_relocation` SHALL be `True`

#### Scenario: Cloud-native executor skips staging and relocation
- **WHEN** a hypothetical `NextflowAdapter` sets both flags to `False`
- **THEN** Canon's pipeline SHALL pass URIs directly to the executor (no `get()` call) and SHALL read the output URI from the executor's result (no `put()` call)

### Requirement: OutputIngestionPipeline uses StorageAdapter for relocation

The `OutputIngestionPipeline` SHALL accept a `StorageAdapter` (or `StorageAdapterRegistry`) at construction time. The `relocate_output()` method SHALL delegate to `storage_adapter.put()` instead of hard-coded type branching. Relocation SHALL only be called when `executor.requires_output_relocation` is `True`.

#### Scenario: Pipeline relocates output via StorageAdapter.put()
- **WHEN** `relocate_output()` is called after a successful CWL execution with `executor.requires_output_relocation = True`
- **THEN** the method SHALL call `storage_adapter.put(local_path, dest_uri)` and return the canonical URI

#### Scenario: Pipeline skips relocation when executor handles it
- **WHEN** `executor.requires_output_relocation = False`
- **THEN** `relocate_output()` SHALL return the URI from the executor's `CWLRunResult.outputs` without calling `put()`

#### Scenario: Pipeline raises CanonStorageError on relocation failure
- **WHEN** `storage_adapter.put()` raises `CanonStorageError`
- **THEN** the pipeline SHALL propagate the error (WorkflowRun marked `failed`)
