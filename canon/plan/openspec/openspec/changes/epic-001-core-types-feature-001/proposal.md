# CanonConfig dataclass implementation

## Goal
CanonConfig dataclass implementation: Implement the CanonConfig dataclass that loads configuration from canon.yaml with validation capabilities.

## Acceptance Criteria
- Given a valid canon.yaml file exists with all required fields and correct types, when CanonConfig is instantiated, then it successfully loads and validates all configuration fields without raising any exceptions
- Given an invalid canon.yaml file with malformed YAML syntax, when CanonConfig attempts to load, then it raises CanonConfigError with a descriptive message containing "yaml" or "parse" indicating the parsing error
- Given an invalid canon.yaml file with missing required fields, when CanonConfig validation runs, then it raises CanonConfigError indicating the specific missing required fields in the message
- Given a canon.yaml file with extra unknown fields not defined in the schema, when CanonConfig attempts to load, then it raises CanonConfigError with descriptive message containing "unknown" or "unexpected" about the unexpected fields
- Given a canon.yaml file with incorrect field types (e.g., string instead of integer), when CanonConfig validation runs, then it raises CanonConfigError indicating the type mismatch for each invalid field with specific field name and expected type in the message

## Constraints
- Complexity: low
