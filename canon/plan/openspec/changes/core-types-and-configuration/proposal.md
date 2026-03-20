## Why

This change introduces the foundational data types, configuration models, and exception hierarchy needed for the Canon system. These core types provide type-safe foundations upon which all other Canon components will be built, ensuring consistent interfaces and reliable behavior across the platform.

## What Changes

- Creation of a new Python module `canon.types` containing all core data models
- Definition of CanonConfig for system configuration
- Implementation of ProductionRule for rule-based processing
- Specification of WildcardBinding for pattern matching
- Development of ValueResolver with URI/Field/Inline/JSON variants
- Creation of CanonTask for task representation
- Definition of ExecutionPlan for execution orchestration
- Implementation of RunHandle and RunStatus for execution tracking
- Development of ExecutorInputs for input handling
- Establishment of all Canon-specific exceptions

## Capabilities

### New Capabilities
- `core-types`: Covers all fundamental data types used throughout the Canon system
- `configuration-models`: Defines how system configuration is structured and validated
- `exception-hierarchy`: Establishes a consistent error handling framework for Canon components

### Modified Capabilities
- None

## Impact

This change introduces core foundational types that will be depended upon by all other Canon modules. The pydantic validation framework ensures type safety across the entire system, reducing runtime errors and improving developer experience. All future development will rely on these models, making them critical for system stability and maintainability.