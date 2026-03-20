# canon-status and canon-rules CLI commands

## Goal
canon-status and canon-rules CLI commands: Implement two remaining CLI commands. canon status reads ~/.canon/runs.db and displays a table of recent runs with run_id, rule_name, status, started_at, and entity counts. canon rules loads and validates canon_rules.yaml and displays a table of all rules with their produces entity type and required input types. canon rules --validate exits 0 if all rules are valid, 1 with error details otherwise.


## Acceptance Criteria
- canon status shows a table with columns: run_id, rule, status, started, inputs, outputs
- canon status shows at most 20 recent runs by default; --limit N overrides
- canon rules shows a table with columns: rule_name, produces_type, requires_types
- canon rules --validate exits 0 for a valid rules file and 1 with error details for invalid
- canon rules --validate on a missing rules file exits 1 with: Rules file not found: <path>
- Both commands support --config <path> to override config file

## Constraints
- Depends on: epic-007-feature-002
- Complexity: low
