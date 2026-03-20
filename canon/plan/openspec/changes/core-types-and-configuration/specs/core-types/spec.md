# Core Types Specification

## Overview
This specification defines the fundamental data models that form the foundation of the Canon system. These are pydantic-based models that provide type safety, validation, and serialization capabilities across all Canon components.

## Requirements

### CanonConfig
- Must support system-wide configuration with validation
- Should allow custom configuration sections
- Needs to support environment variable interpolation
- Must be serializable to multiple formats (JSON/YAML)

### ProductionRule
- Should define rule-based processing patterns
- Must support pattern matching with wildcards
- Needs to be extensible for different rule types
- Must provide clear error handling and validation

### WildcardBinding
- Required to support pattern matching in rules
- Should handle variable binding during rule execution
- Must support multiple wildcard patterns
- Needs serialization support

### ValueResolver Variants
- URIResolver: Resolve values using URI references
- FieldResolver: Extract values from structured data fields
- InlineResolver: Handle literal inline values
- JSONResolver: Parse and extract values from JSON structures
- All variants must share common interface while supporting specific behaviors

### CanonTask
- Should represent a unit of work in the system
- Must support dependency tracking between tasks
- Needs execution metadata and status reporting
- Required to be serializable for persistence

### ExecutionPlan
- Must orchestrate task execution flows
- Should support parallel and sequential execution patterns
- Needs dependency resolution capabilities
- Must provide planning validation

### RunHandle and RunStatus
- Required for tracking execution lifecycle
- Should provide atomic run state management
- Must support concurrent access control
- Needs serialization of state information

### ExecutorInputs
- Should handle input preparation for task execution
- Must support input transformation and validation
- Required to manage input caching strategies
- Needs flexible input type support

## Acceptance Criteria
- All models must pass pydantic validation with appropriate error handling
- Models must be serializable to JSON and YAML formats
- All models must include comprehensive documentation and docstrings
- Models must be compatible across all supported Python versions
- All types must follow consistent naming and structure conventions

## Design Considerations
- Minimize circular dependencies between type definitions
- Ensure extensibility through inheritance or composition patterns
- Maintain backward compatibility where possible
- Provide clear feedback for validation errors