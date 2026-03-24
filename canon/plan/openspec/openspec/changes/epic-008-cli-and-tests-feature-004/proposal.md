# Canon Rules Command Implementation

## Goal
Canon Rules Command Implementation: Implement canon rules list and canon rules validate CLI commands for inspecting and validating the canon_rules.yaml rule registry.

## Acceptance Criteria
- Given a valid canon_rules.yaml, when the user runs canon rules list, then each rule is printed with its name, entity_type, and a summary of its produces.match parameters
- Given a valid canon_rules.yaml and all referenced CWL files exist, when the user runs canon rules validate, then it exits with code 0 and prints a success message
- Given a canon_rules.yaml with an unpropagated wildcard error, when the user runs canon rules validate, then it exits with a non-zero code and prints the rule name, wildcard name, and which requires entry contains the unpropagated wildcard
- Given a canon_rules.yaml with a tool reference missing a version, when validated, then CanonRuleValidationError is reported with the rule name and the offending entity reference expression
- Given canon rules validate finds multiple errors, when it reports them, then all errors are printed together before the command exits rather than stopping at the first

## Constraints
- Complexity: medium
