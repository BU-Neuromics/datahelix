# RecursivePlanner core resolve algorithm

## Goal
RecursivePlanner core resolve algorithm: Implements the basic recursive planning logic for resolving entities with dependency chains, including the foundational BUILD and REUSE decision-making capabilities.

## Acceptance Criteria
- Given a dependency chain with exactly 2 entities where the first entity needs to be built and the second can be reused, when the planner resolves the chain, then the complete chain is returned with the first entity marked as BUILD and the second as REUSE
- Given an entity with no dependencies, when the planner resolves the entity, then the entity is returned as-is in a plan with no additional dependency resolution steps
- Given a complex dependency chain with 5 levels where each level has different decision types (BUILD/REUSE), when the planner resolves all levels, then all 5 levels are resolved correctly with appropriate BUILD/REUSE decisions for each entity
- Given a dependency chain with 2 entities where both entities can be reused, when the planner resolves the chain, then the complete chain is returned with both entities marked as REUSE
- Given a dependency chain with 3 entities where the first needs to be built, the second can be reused, and the third needs to be built, when the planner resolves the chain, then the complete chain is returned with appropriate BUILD/REUSE decisions for each entity
- Given a single entity with no dependencies in a complex environment, when the planner resolves the entity, then the entity is returned as-is properly formatted in the plan output
- Given a complex dependency chain with 5 levels where all entities must be built, when the planner resolves all levels, then all 5 levels are resolved correctly with all entities marked as BUILD
- Given a dependency chain with 2 entities where the first entity can be reused and the second needs to be built, when the planner resolves the chain, then the complete chain is returned with the first entity marked as REUSE and the second as BUILD
- Given an empty dependency chain, when the planner attempts to resolve it, then an appropriate error is raised or handled gracefully
- Given a circular dependency in the chain, when the planner attempts to resolve it, then an exception is thrown indicating the circular dependency

## Constraints
- Complexity: medium
