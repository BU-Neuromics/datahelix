# Exception Hierarchy Implementation

## Goal
Exception Hierarchy Implementation: Create a structured exception hierarchy extending Pydantic's validation errors for canon-specific error types.

## Acceptance Criteria
- Given a CanonRuleValidationError is instantiated with a field name and error type, when the error message is rendered via str() or repr(), then it contains both the field name and the error type as distinct, parseable substrings
- Given a CanonRuleValidationError wraps a Pydantic ValidationError, when the exception's attributes are inspected, then it exposes the original Pydantic ValidationError via a dedicated attribute (e.g. __cause__ or a custom field) without modification
- Given a CanonRuleValidationError is raised and caught, when the traceback is printed, then the full call stack from the raise site is preserved and visible in the traceback output
- Given a CanonResolutionError is instantiated with a task_id and component_name, when the exception's attributes are accessed, then task_id and component_name are available as typed attributes matching the values passed at construction
- Given a CanonResolutionError wraps an underlying system error, when the exception is inspected, then the original error is accessible via __cause__ (standard chaining) and the error_type and description are available as structured attributes
- Given a CanonExecutionError is raised inside a nested call stack within a canon component, when the exception propagates to the caller, then the complete call stack from the original raise site is intact in the traceback
- Given a CanonExecutionError is instantiated with component-specific context (e.g. component_name, operation, input_data), when the exception's structured data is accessed, then all context fields are retrievable as a dict or typed attributes without parsing the message string
- Given any canon exception class (CanonRuleValidationError, CanonResolutionError, CanonExecutionError), when its class hierarchy is inspected, then it is a subclass of a common CanonError base class which itself extends Exception
- Given any canon exception is serialized to a dict or JSON via a to_dict() method, when the output is examined, then it contains at minimum the keys error_type, message, and context with non-null values

## Constraints
- Complexity: low
