# Rules file loader and validator

## Goal
Rules file loader and validator: Implement a RulesLoader that reads canon_rules.yaml, parses each rule as a ProductionRule, validates the structure, and raises CanonValidationError with per-rule details for any invalid rules. Rules file may contain multiple rules. Loader reports all validation errors at once (not fail-fast).


## Acceptance Criteria
- Given a valid canon_rules.yaml with 3 rules, RulesLoader returns a list of 3 ProductionRule objects
- Given a rules file with one invalid rule (missing execute.workflow), the error message names the rule and the missing field
- Given a non-existent rules file path, CanonValidationError is raised with the file path
- RulesLoader.from_file(path) is the primary constructor
- All validation errors across all rules are collected and returned in a single CanonValidationError

## Constraints
- Depends on: epic-001-feature-002
- Complexity: low
