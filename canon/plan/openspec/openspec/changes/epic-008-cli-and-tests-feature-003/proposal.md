# Canon Plan Command Implementation

## Goal
Canon Plan Command Implementation: Implement the canon plan CLI command for dry-run REUSE/BUILD tree display without executing any CWL workflows.

## Acceptance Criteria
- Given a valid canon.yaml and Hippo instance, when the user runs canon plan AlignmentFile with full --param arguments, then the command prints the dependency tree showing REUSE or BUILD for each node and exits with code 0
- Given a dependency tree where some inputs exist in Hippo and some do not, when canon plan output is inspected, then REUSE nodes show the matched entity UUID and BUILD nodes show the matching rule name and CWL workflow path
- Given the summary line of canon plan output, when printed, then it shows the count of BUILD executions required and REUSE nodes that will be skipped
- Given CanonResolutionError occurs during dry-run resolution, when canon plan handles it, then the error is shown inline in the tree at the failing node and the command exits with a non-zero code
- Given no CWL workflow is executed by canon plan, when the command completes, then the Hippo entity registry is unchanged and no WorkflowRun entities are created

## Constraints
- Complexity: medium
