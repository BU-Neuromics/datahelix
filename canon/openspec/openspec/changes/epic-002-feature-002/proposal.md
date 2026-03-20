# RulesEngine — rule indexing and lookup

## Goal
RulesEngine — rule indexing and lookup: Implement RulesEngine that wraps a list of ProductionRule and provides find_rules(entity_type, metadata_spec) to return candidate rules whose produces section matches the requested entity_type. For v0.1, matching is by entity_type equality only; wildcard fields in produces.metadata are not filtered at this stage (binding resolution happens in the planner). Also implement rules() to list all rules and validate() to check for duplicate rule names.


## Acceptance Criteria
- RulesEngine.find_rules("AlignmentFile", {}) returns all rules with produces.entity_type == "AlignmentFile"
- RulesEngine.find_rules("NonexistentType", {}) returns an empty list
- RulesEngine.validate() raises CanonValidationError if two rules share the same name
- RulesEngine.rules() returns all loaded ProductionRule objects
- RulesEngine is constructable from a list of ProductionRule objects or via RulesEngine.from_file(path)

## Constraints
- Depends on: epic-002-feature-001
- Complexity: low
