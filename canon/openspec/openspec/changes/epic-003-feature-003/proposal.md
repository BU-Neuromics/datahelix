# SemanticPlanner — REUSE/BUILD decision and recursive resolution

## Goal
SemanticPlanner — REUSE/BUILD decision and recursive resolution: Implement SemanticPlanner.plan(entity_type, metadata_spec) which first queries Hippo for an existing matching entity (REUSE), and if none found, selects a production rule from RulesEngine (BUILD) and recursively plans each required input. Returns an ExecutionPlan DAG. If no rule can produce the requested entity type, raises CanonPlanningError. If multiple rules match, the first match is used for v0.1.


## Acceptance Criteria
- Given an existing Hippo entity matching the spec, plan() returns an ExecutionPlan with a single REUSE node
- Given no existing entity but a matching rule, plan() returns an ExecutionPlan with a BUILD node for the target and REUSE/BUILD nodes for its inputs
- Given a 3-level dependency chain, plan() returns a correctly ordered ExecutionPlan
- Given a request with no matching rule and no existing entity, CanonPlanningError is raised naming the entity type
- SemanticPlanner requires HippoClient and RulesEngine at construction time

## Constraints
- Depends on: epic-003-feature-001, epic-003-feature-002, epic-002-feature-002, epic-001-feature-004
- Complexity: high
