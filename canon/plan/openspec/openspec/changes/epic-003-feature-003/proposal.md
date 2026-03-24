# Wildcard Propagation Validation

## Goal
Wildcard Propagation Validation: Validate that wildcards are properly propagated through rules and sidecars with precise error reporting when inconsistencies occur.

## Acceptance Criteria
- Given a rule containing a wildcard pattern (e.g., "{sample}") in a field that requires propagation to child or sidecar fields, when the RulesLoader validates that rule, then it raises an UnpropagatedWildcardError whose message includes the exact field path (e.g., "rule.outputs[0].path") and the unpropagated wildcard token
- Given a rule with a wildcard in an input field that does not appear in the corresponding output field where propagation is required, when the RulesLoader validates the rule, then the error diagnostic identifies both the source field path containing the wildcard and the target field path missing it
- Given a ruleset of three or more rules where two rules have unpropagated wildcards in different fields, when the RulesLoader processes the entire ruleset, then it reports exactly two UnpropagatedWildcardError diagnostics, each with the correct rule identifier and field path
- Given a rule with a wildcard that is correctly propagated through all required fields including sidecar declarations, when the RulesLoader validates it, then validation completes successfully with no errors or warnings
- Given a sidecar definition referencing a wildcard from its parent rule, when the wildcard is present in the parent rule but missing from the sidecar's corresponding field, then the RulesLoader raises an UnpropagatedWildcardError with a field path prefixed by the sidecar identifier (e.g., "rule.sidecars[log].path")
- Given a rule containing multiple distinct wildcard tokens (e.g., "{sample}" and "{lane}") where only one fails to propagate, when the RulesLoader validates the rule, then the error diagnostic references only the unpropagated wildcard token and does not flag the correctly propagated one
- Given a rule with nested wildcard propagation across two levels (e.g., rule to sub-rule to sidecar), when all wildcards propagate correctly at every level, then validation passes without errors
- Given a rule where a wildcard token appears in a field that does not require propagation, when the RulesLoader validates it, then no UnpropagatedWildcardError is raised for that field

## Constraints
- Complexity: high
