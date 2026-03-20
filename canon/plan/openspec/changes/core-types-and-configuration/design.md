## Context

This change introduces foundational data types and configuration models for the Canon system. The module `canon.types` will serve as the core type-safe foundation upon which all other Canon components are built. Using Pydantic for validation ensures consistency, reliability, and maintainability. The core types include configuration models, execution planning structures, task representations, and an exception hierarchy.

## Goals / Non-Goals

**Goals:**
- Create a comprehensive set of pydantic-based data models for the Canon system
- Establish a consistent type-safe interface across all Canon components
- Provide clear configuration models for system behavior
- Implement proper exception hierarchy for error handling
- Ensure all core types are well-documented and testable

**Non-Goals:**
- Implementation of business logic or processing algorithms
- Specific API endpoints or external interfaces (these will be built on top of these types)
- Runtime execution details beyond the data structures

## Decisions

**Type System Selection**: Pydantic v2 has been chosen as the primary type system due to:
- Excellent validation capabilities with clear error messages
- Integration with Python type hints
- Built-in serialization support for JSON and other formats
- Active maintenance and community support

**Module Structure**: The `canon.types` module will contain:
- Core data models for configuration and execution
- Enum types for status indicators and resolver variants
- Exception hierarchy extending base Python exceptions
- Supporting utilities for type validation

**Data Model Organization**:
- `CanonConfig`: Main system configuration with validation
- `ProductionRule`: Rule-based processing definitions
- `WildcardBinding`: Pattern matching capabilities
- `ValueResolver` variants: URI, Field, Inline, and JSON resolvers for flexible value resolution
- `CanonTask`: Task representation for execution
- `ExecutionPlan`: Orchestration of tasks and their execution flow
- `RunHandle` and `RunStatus`: Execution lifecycle tracking
- `ExecutorInputs`: Input handling infrastructure

**Inheritance Strategy**: Custom exceptions will inherit from appropriate base Python exception types (ValueError, RuntimeError) to maintain consistency with Python's standard exception hierarchy.

## Risks / Trade-offs

- **Complexity vs. Flexibility**: The extensive use of inheritance and variants in ValueResolver may increase complexity. However, this trade-off provides maximum flexibility for different input handling approaches.
  → Mitigation: Comprehensive unit tests and clear documentation
- **Pydantic Version Compatibility**: Pydantic v2 introduces breaking changes from v1. We will document these as part of the module's requirements.
  → Mitigation: Clear version pinning and thorough testing
- **Circular Dependencies**: The interconnected nature of these models could lead to circular imports.
  → Mitigation: Careful import structure with forward references and strategic dependency management

## Migration Plan

1. Create the `canon.types` Python module as a new dependency
2. Update existing projects to depend on this new module
3. Refactor existing code to use these new types instead of ad-hoc models
4. Run comprehensive test suite to ensure no regressions

## Open Questions

- Should certain components like `ValueResolver` be made generic to support more advanced typing?
- What level of runtime validation should be included in each model?
- How should we handle versioned configuration schemas for future compatibility?