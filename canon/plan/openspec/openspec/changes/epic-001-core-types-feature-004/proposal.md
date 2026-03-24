# CanonSpec dataclass implementation

## Goal
CanonSpec dataclass implementation: Implement the CanonSpec dataclass that serves as the core representation of canonical specifications.

## Acceptance Criteria
- Given a valid configuration schema with proper field types and required parameters, when CanonSpec is initialized with valid data, then it correctly validates all fields and stores the specification structure without raising any validation errors
- Given incompatible parameter types are mixed in specification such as assigning a string value to an integer field, when validation runs on invalid data, then it raises a TypeError with specific field details indicating which field failed validation and the expected type
- Given CanonSpec contains nested objects and lists with various valid data types, when serialized to YAML and then deserialized back into Python objects, then all original content is preserved with correct data types and no information loss occurs
- Given CanonSpec has default values defined for optional fields, when initialized without providing those fields, then it correctly applies the default values and validates them against the schema
- Given CanonSpec validation encounters missing required fields, when validation runs on incomplete data, then it raises a ValueError with clear message indicating which required field is missing and its expected type
- Given CanonSpec contains enum fields with predefined acceptable values, when invalid enum value is provided, then validation raises a ValueError with detailed information about valid options for that field
- Given CanonSpec has fields with complex validation rules such as regex patterns or custom validators, when invalid data is provided, then it raises appropriate validation exceptions with descriptive messages about the rule violation
- Given CanonSpec contains circular references in nested structures, when serialization occurs on data with circular references, then it correctly handles the circular references without infinite recursion errors
- Given CanonSpec has fields that are lists of objects with their own schemas, when validation runs on list items, then each item is validated against its respective schema and invalid items raise appropriate errors with item index details

## Constraints
- Complexity: medium
