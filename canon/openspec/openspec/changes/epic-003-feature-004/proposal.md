# Cycle detection in dependency graph

## Goal
Cycle detection in dependency graph: Implement DFS-based cycle detection in SemanticPlanner. While recursively resolving dependencies, track which entity_type+metadata combinations are currently being resolved (the "grey" set in DFS colouring). If a dependency is encountered that is already in the grey set, raise CanonCycleError naming the cycle path.


## Acceptance Criteria
- Given rule A requires output of rule B and rule B requires output of rule A, CanonCycleError is raised during plan()
- CanonCycleError includes the cycle path as a list of entity type + metadata spec strings
- Given a valid DAG with shared dependencies (diamond pattern), no false cycle is detected
- Cycle detection adds no observable latency for acyclic graphs with up to 10 rules
- The cycle check works correctly when the same entity type appears as input to multiple rules at different levels

## Constraints
- Depends on: epic-003-feature-003
- Complexity: medium
