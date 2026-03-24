# Implement CanonReferenceLoader

## Goal
Implement CanonReferenceLoader: Create the CanonReferenceLoader class in loader.py that implements the hippo.reference_loaders entry point and installs the schema.

## Acceptance Criteria
- Given a Python environment with the canon package installed, when inspecting the hippo.reference_loaders entry point group, then an entry named "canon" exists and points to the CanonReferenceLoader class in loader.py
- Given a CanonReferenceLoader instance and a valid schema directory containing all five entity-type YAML files (Tool, ToolVersion, GenomeBuild, GeneAnnotation, WorkflowRun), when the loader's install method is invoked against a running local Hippo test instance, then the method completes without raising an exception and returns a result indicating success
- Given the install method has completed successfully against a Hippo test instance, when querying the Hippo API for registered entity types, then all five types (Tool, ToolVersion, GenomeBuild, GeneAnnotation, WorkflowRun) are present, each with its name, description, and field definitions matching the source schema files
- Given a CanonReferenceLoader instance, when the install method is called with a schema_path that does not exist on the filesystem, then a FileNotFoundError (or equivalent) is raised whose message includes the invalid path string
- Given a CanonReferenceLoader instance and a schema directory that exists but is missing one or more required entity-type schema files, when the install method is called, then a ConfigurationError is raised whose message lists the names of the missing schema files
- Given a Hippo test instance that already has the canon schema installed at version N, when the install method is called again with an identical schema directory, then the operation is idempotent — no duplicate entity types are created and the method completes without error
- Given the CLI is available, when a researcher runs `hippo reference install canon --schema-dir <valid-path>` against a local Hippo test instance, then the command exits with code 0, prints a summary line for each registered entity type, and all five entity types are queryable in Hippo afterward
- Given the CLI is available, when a researcher runs `hippo reference install canon --schema-dir <nonexistent-path>`, then the command exits with a non-zero code and prints an error message containing the invalid path

## Constraints
- Complexity: medium
