# ToolVersion Entity Schema Definition

## Goal
ToolVersion Entity Schema Definition: Define the LinkML schema for the ToolVersion entity type with required fields and validation rules.

## Acceptance Criteria
- Given a LinkML schema file exists for Hippo entity types, when a ToolVersion class is defined with fields version (string, required), tool_id (string, required), and created_at (datetime, required), then the schema passes `linkml-lint` validation with zero errors
- Given the ToolVersion class is defined in the schema, when a valid instance is submitted with version "1.2.3", a non-empty tool_id, and a valid ISO-8601 datetime for created_at, then `linkml-validate` accepts the instance without errors
- Given the ToolVersion class is defined in the schema, when an instance is submitted with version set to "not-a-version" (failing the semver pattern constraint), then `linkml-validate` rejects the instance and the error message references the version field and the expected pattern
- Given the ToolVersion class is defined in the schema, when an instance is submitted with the required field version omitted, then `linkml-validate` rejects the instance and the error message identifies version as a missing required field
- Given the ToolVersion class is defined in the schema, when a developer attempts to add a new field with no range (type) specified to the ToolVersion class, then `linkml-lint` reports a validation error identifying the untyped field
- Given the ToolVersion class is defined and passes validation, when the schema is compiled to JSON Schema via `gen-json-schema`, then the generated JSON Schema contains a ToolVersion definition with version, tool_id, and created_at listed in the required array and each property has the correct type (string, string, string with format date-time respectively)

## Constraints
- Depends on: feature-001
- Complexity: low
