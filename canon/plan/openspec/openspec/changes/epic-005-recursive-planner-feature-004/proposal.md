# Dry-run output with dependency tree

## Goal
Dry-run output with dependency tree: Implement canon plan dry-run output that displays the complete dependency tree with REUSE/BUILD decisions at each node before any CWL execution is performed.

## Acceptance Criteria
- Given a canon plan request for AlignmentFile with two required inputs that already exist as registered entities in Hippo, when dry-run mode is executed, then each leaf node in the output tree displays status REUSE with the entity UUID and Hippo URI, and the root node displays status BUILD with the matched rule name and the absolute CWL workflow path
- Given a dependency tree containing a mix of REUSE and BUILD nodes, when the dry-run summary line is printed after the tree, then it displays the exact count of BUILD nodes labeled as CWL executions required and the exact count of REUSE nodes labeled as zero executions required, and the two counts sum to the total number of nodes in the tree
- Given a resolution path where a required input has no matching rule and no existing entity in Hippo, when canon plan is run in dry-run mode, then the tree displays an ERROR status at the failing node with the message "CanonNoRuleError" and the entity type that could not be resolved, and no CWL execution is attempted for any node in the tree
- Given a dependency tree with exactly 3 levels (root at depth 0, children at depth 1, grandchildren at depth 2), when dry-run output is generated, then each node is indented by exactly 2 spaces per depth level so that root has 0-space indent, depth-1 nodes have 2-space indent, and depth-2 nodes have 4-space indent
- Given a successful dry-run where at least one node has status BUILD, when the output is printed to stdout, then each BUILD node displays the matched rule name, the absolute path to the CWL workflow file, and each resolved parameter key-value pair that was used for rule matching
- Given a canon plan request run with the --dry-run flag, when execution completes, then no CWL workflow is submitted, no new entities are registered in Hippo, and the process exit code is 0
- Given a dependency tree where a subtree rooted at a BUILD node contains both REUSE and further BUILD children, when dry-run output is generated, then parent-child relationships are visually represented via indentation and every child node appears directly beneath its parent at the correct indent level

## Constraints
- Complexity: low
