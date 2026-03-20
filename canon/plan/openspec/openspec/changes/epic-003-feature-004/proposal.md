# Cycle detection in dependency graph

## Goal
Cycle detection in dependency graph: Implement DFS-based cycle detection in SemanticPlanner. While recursively resolving dependencies, track which entity_type+metadata combinations are currently being resolved (the "grey" set in DFS colouring). If a dependency is encountered that is already in the grey set, raise CanonCycleError naming the cycle path.

## Acceptance Criteria
- Given two rules where rule A requires output of rule B and rule B requires output of rule A, when plan() is called, then CanonCycleError is raised
- Given CanonCycleError is raised for a cycle, when accessing the error, then the cycle path is included as a list of entity type + metadata spec strings
- Given a valid DAG with shared dependencies in diamond pattern, when plan() is called, then no false cycle is detected
- Given an acyclic graph with up to 10 rules, when plan() is called, then cycle check adds no observable latency
- Given the same entity type appears as input to multiple rules at different levels, when plan() is called, then cycle detection works correctly

## Constraints
- Depends on: epic-003-feature-003
- Complexity: medium
