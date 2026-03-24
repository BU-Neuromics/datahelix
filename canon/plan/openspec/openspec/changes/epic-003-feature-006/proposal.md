# Startup Validation Performance

## Goal
Startup Validation Performance: Ensure startup validation catches all defined error categories and completes within target time limit (500ms for 50 rules/50 sidecars).

## Acceptance Criteria
- Given a canon_rules.yaml containing exactly 50 rules and 50 sidecar definitions, when the RulesLoader performs full startup validation on standard laptop hardware (4-core CPU, 16 GB RAM, SSD), then the entire validation pass completes in under 500ms wall-clock time as measured by an instrumented timer wrapping the validation entry point
- Given a canon_rules.yaml containing 50 rules and 50 sidecars where at least one rule uses a wildcard pattern that has not been propagated to its dependent rules, when the RulesLoader runs startup validation, then it emits a diagnostic error of category "unpropagated_wildcard" that identifies the offending rule by id and the specific wildcard expression that was not propagated
- Given a canon_rules.yaml where at least one rule references an identity_field that does not exist in the corresponding entity schema, when the RulesLoader runs startup validation, then it emits a diagnostic error of category "invalid_identity_field" that names the rule id, the invalid field reference, and the entity type it was expected to belong to
- Given a canon_rules.yaml containing multiple errors across different categories (unpropagated wildcards, invalid identity_field references, and at least one other defined error category), when the RulesLoader runs startup validation, then it collects and reports all errors from all categories in a single validation pass rather than stopping at the first error encountered
- Given a canon_rules.yaml containing zero errors, when the RulesLoader runs startup validation, then it returns a success result with no diagnostic errors and completes within the 500ms time budget
- Given a canon_rules.yaml that is scaled to 100 rules and 100 sidecars (2x the baseline), when the RulesLoader runs startup validation, then it completes in under 1200ms, demonstrating sub-quadratic scaling relative to the 500ms baseline at 50/50
- Given that startup validation has completed with one or more errors, when the caller inspects the validation result, then each error entry includes at minimum the fields rule_id, error_category, message, and source_location (file and line number or YAML path) sufficient for a developer to locate and fix the issue without additional debugging

## Constraints
- Complexity: high
