# Define Tool Entity Type

## Goal
Define Tool Entity Type: Implement the Tool entity type definition in schema.yaml with required fields including name, version, and description.

## Acceptance Criteria
- Given the schema.yaml file exists, when a developer inspects the Tool entity type definition, then it contains exactly three fields named "name", "version", and "description", each with type "string" and required set to true
- Given a Tool entity is instantiated with all three required fields populated with non-empty string values, when schema validation runs against the instance, then validation passes with zero errors
- Given a Tool entity is instantiated with the "name" field missing, when schema validation runs, then validation fails and the error message explicitly identifies "name" as a missing required field
- Given a Tool entity is instantiated with the "version" field set to a non-string value (e.g., integer 2), when schema validation runs, then validation fails and the error message identifies a type mismatch on "version"
- Given a Tool entity with all required fields populated with valid strings is saved to the database, when the record is retrieved by its identifier, then the returned record contains "name", "version", and "description" fields with values identical to those provided at save time
- Given the schema.yaml file is loaded, when the file is validated against the meta-schema (LinkML or project schema rules), then no validation errors are reported for the Tool entity definition

## Constraints
- Complexity: low
