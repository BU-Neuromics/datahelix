# Canon Plan Command Implementation

## Goal
Canon Plan Command Implementation: Implement the canon plan CLI command for dry-run REUSE/BUILD tree display without executing any CWL workflows.

## Acceptance Criteria
- Given a valid canon.yaml and Hippo instance, when the user runs canon plan AlignmentFile with full --param arguments, then the command prints the dependency tree showing REUSE or BUILD for each node and exits with code 0
- Given a dependency tree where some inputs exist in Hippo and some do not, when canon plan output is inspected, then REUSE nodes show the matched entity UUID and BUILD nodes show the matching rule name and CWL workflow path in the format "BUILD <EntityType> (rule=<rule_name>, cwl=<workflow_path>)"
- Given the summary line of canon plan output, when printed, then it shows the count of BUILD executions required and REUSE nodes that will be skipped
- Given CanonResolutionError occurs during dry-run resolution, when canon plan handles it, then the error is shown inline in the tree at the failing node and the command exits with a non-zero code
- Given no CWL workflow is executed by canon plan, when the command completes, then the Hippo entity registry is unchanged and no WorkflowRun entities are created
- Given the default human-readable output mode, when the tree is rendered to a terminal, then each nesting level is indented by two spaces with UTF-8 box-drawing characters (├──, └──, │) connecting parent to children, and colour output is enabled when stdout is a TTY and disabled otherwise or when the --no-color flag is passed
- Given the user runs canon plan with --format json, when the output is parsed, then it is a valid JSON object containing a "tree" key whose value is a nested object where each node has "entity_type", "params", "action" (REUSE or BUILD), and a "children" array of child nodes in the same schema, representing the full dependency tree recursively
- Given the user runs canon plan with --format set to an unsupported value (e.g. --format xml), then the command exits with a non-zero code and prints an error to stderr listing the supported format values (human, json)

## Constraints
- Depends on: epic-001-core-types-feature-002, epic-004-entity-ref-resolver-feature-001, epic-005-recursive-planner-feature-001
- Complexity: medium
