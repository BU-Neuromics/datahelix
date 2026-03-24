# RecursivePlanner core resolve algorithm

## Goal
RecursivePlanner core resolve algorithm: Implements the basic recursive planning logic for resolving entities with dependency chains, including the foundational BUILD and REUSE decision-making capabilities.

## Acceptance Criteria
- Given an entity with no dependencies, when the planner resolves the entity, then the plan output contains exactly one entry for that entity with its original properties preserved and no additional dependency resolution steps
- Given a dependency chain of 2 entities where the first entity has no existing valid instance (requires BUILD) and the second has an existing valid instance (eligible for REUSE), when the planner resolves the chain, then the returned plan contains both entities in dependency order with the first marked BUILD and the second marked REUSE
- Given a dependency chain of 2 entities where both entities have existing valid instances, when the planner resolves the chain, then both entities are marked REUSE and no build steps are generated for either entity
- Given a dependency chain of 2 entities where the first entity has an existing valid instance (REUSE) and the second requires creation (BUILD), when the planner resolves the chain, then the first entity is marked REUSE and the second is marked BUILD, and the plan reflects the correct dependency ordering
- Given a dependency chain of 3 entities A→B→C where A requires BUILD, B is eligible for REUSE, and C requires BUILD, when the planner resolves the chain, then the plan contains all three entities with decisions BUILD, REUSE, and BUILD respectively, and each entity's position in the plan reflects its dependency depth
- Given a dependency chain of 5 levels where each level alternates between BUILD and REUSE decisions, when the planner resolves all levels, then all 5 levels appear in the plan with correct BUILD/REUSE decisions matching each entity's reuse eligibility, and the resolution order proceeds from deepest dependency to root
- Given a dependency chain of 5 levels where no entity has an existing valid instance, when the planner resolves all levels, then all 5 entities are marked BUILD and the plan orders them from deepest dependency first to root last
- Given an empty dependency chain (no entities provided), when the planner attempts to resolve it, then the planner raises a ValueError (or equivalent validation error) with a message indicating that the input chain is empty
- Given a dependency chain containing a circular reference (e.g., A depends on B, B depends on A), when the planner attempts to resolve it, then the planner raises a CircularDependencyError (or equivalent) identifying the entities involved in the cycle before any BUILD/REUSE decisions are made
- Given a single entity whose reuse eligibility check fails with an unexpected error, when the planner resolves the entity, then the error propagates with context identifying which entity failed, and no partial plan is returned

## Constraints
- Complexity: medium
