# ResolvedInput dataclass

## Goal
ResolvedInput dataclass: Implement the ResolvedInput dataclass used for handling resolved parameter inputs in Canon specifications.

## Acceptance Criteria
- Given a parameter set is provided with valid string values, when ResolvedInput is instantiated, then it correctly stores all parameter values and provides access to them via attribute lookup
- Given a parameter set contains entity references that can be resolved to User entities, when ResolvedInput is accessed, then it properly translates references to actual User objects using the canon resolver
- Given a parameter set fails validation rules for required fields, when validation is executed on ResolvedInput, then it raises a ValidationException with field name "required_field" and error message "This field is required"
- Given a ResolvedInput object is created with missing required parameters, when accessing non-existent attributes, then it raises an AttributeError with message "ResolvedInput has no attribute 'missing_attr'"
- Given a ResolvedInput object contains invalid parameter types for a field, when validation runs, then it raises TypeError with parameter name "integer_field" and expected type "int"
- Given a ResolvedInput object has circular references in entity resolution involving User and Group, when accessing resolved entities, then it raises a CircularReferenceError with message containing "circular reference detected between User and Group"
- Given a ResolvedInput object is created with nested parameter structures including lists of entities, when accessed, then it preserves nested structure and resolves nested entity references properly
- Given a ResolvedInput object contains empty string values for optional parameters, when validation runs, then it allows empty values and does not raise validation errors
- Given multiple ResolvedInput objects are created with identical parameters, when compared using equality operators, then they return True if all resolved values match exactly
- Given a ResolvedInput object is serialized to JSON, when deserialized back, then it reconstructs the original object with identical resolved attributes and entity references

## Constraints
- Complexity: medium
