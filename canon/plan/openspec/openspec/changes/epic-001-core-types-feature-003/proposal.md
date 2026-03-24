# Parameter type dataclasses

## Goal
Parameter type dataclasses: Implement parameter types including ScalarParam, EntityRefParam, and WildcardParam dataclasses.

## Acceptance Criteria
- Given a scalar parameter definition with a valid numeric value is provided, when ScalarParam is instantiated with that value, then it correctly stores the numeric value and passes validation
- Given a scalar parameter definition with a string value is provided, when ScalarParam is instantiated with that value, then it correctly stores the string value and passes validation
- Given an entity reference parameter definition with a valid reference format is provided, when EntityRefParam is constructed with that reference, then it properly parses and stores the entity reference components (type, id)
- Given an entity reference parameter definition with an invalid reference format is provided, when EntityRefParam is constructed with that reference, then it raises a validation error
- Given a wildcard parameter configuration with a valid pattern is provided, when WildcardParam is created with that pattern, then it correctly stores the pattern and validates matching against wildcard expressions
- Given a scalar parameter with an invalid value type is provided, when ScalarParam is instantiated, then it raises a validation error
- Given an entity reference parameter with a null or empty value is provided, when EntityRefParam is constructed, then it raises a validation error
- Given a wildcard parameter with no pattern is provided, when WildcardParam is created, then it raises a validation error

## Constraints
- Complexity: medium
