# Dry-run output with dependency tree

## Goal
Dry-run output with dependency tree: Implement canon plan dry-run output that displays the complete dependency tree with REUSE/BUILD decisions at each node before any CWL execution is performed.

## Acceptance Criteria
- Given a canon plan request for AlignmentFile with two required inputs that exist in Hippo, when dry-run output is generated, then each node in the tree shows REUSE with the entity UUID and URI, and the top-level shows BUILD with the rule name and CWL path
- Given a dependency tree where some nodes are REUSE and some are BUILD, when the dry-run summary is printed, then it shows the count of BUILD nodes (CWL executions) and REUSE nodes (zero executions) separately
- Given a resolution that would trigger CanonNoRuleError for a required input, when canon plan is run in dry-run mode, then the error is shown in the tree at the failing node without performing any execution
- Given a dependency tree with 3 levels, when dry-run output is generated, then the indentation of each node reflects its depth in the dependency tree
- Given a successful dry-run, when the output is printed to stdout, then each BUILD node shows the matched rule name, the CWL workflow path, and the resolved parameter values used for matching

## Constraints
- Complexity: low
