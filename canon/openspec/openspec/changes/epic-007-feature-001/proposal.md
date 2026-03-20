# canon-plan CLI command

## Goal
canon-plan CLI command: Implement the canon plan CLI command. Accepts a target specification as --entity-type and --metadata (key=value pairs). Invokes SemanticPlanner.plan() and renders the resulting ExecutionPlan as a rich tree showing each node as REUSE (green, with entity ID) or BUILD (yellow, with rule name and wildcard bindings). Exits 0 on success, 1 on planning error. Supports --rules and --config flags.


## Acceptance Criteria
- canon plan --entity-type AlignmentFile --metadata sample_id=S001 genome_build=hg38 prints a plan tree
- REUSE nodes display the existing entity ID and entity type in green
- BUILD nodes display the rule name and bound wildcard values in yellow
- canon plan exits with code 1 and an error message if planning fails
- --config <path> overrides the default canon.yaml config file path
- --rules <path> overrides the default rules file path

## Constraints
- Depends on: epic-003-feature-003, epic-003-feature-004
- Complexity: medium
