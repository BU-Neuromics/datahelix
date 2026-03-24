# Canon Rules Command Implementation

## Goal
Canon Rules Command Implementation: Implement canon rules list and canon rules validate CLI commands for inspecting and validating the canon_rules.yaml rule registry.

## Acceptance Criteria
- Given a valid canon_rules.yaml containing at least two rules, when the user runs `canon rules list`, then each rule is printed on its own line showing the rule name, entity_type, and a comma-separated summary of its produces.match parameter keys and glob patterns
- Given a valid canon_rules.yaml containing rules with different entity_types, when the user runs `canon rules list`, then the output lists every rule defined in the file with no omissions and no duplicates
- Given a valid canon_rules.yaml where all referenced CWL tool files exist on disk and all entity references include versions, when the user runs `canon rules validate`, then the command exits with code 0 and prints a single-line success message to stdout indicating the number of rules validated
- Given a canon_rules.yaml where a rule defines a wildcard in its requires block but does not propagate that wildcard into the corresponding produces.match block, when the user runs `canon rules validate`, then the command exits with a non-zero exit code and the error output includes the rule name, the unpropagated wildcard name, and the specific requires entry that contains it
- Given a canon_rules.yaml where a rule's tool reference uses an entity reference expression that omits the version component (e.g. `entity://tool/bwa` instead of `entity://tool/bwa@0.7.17`), when the user runs `canon rules validate`, then a CanonRuleValidationError is reported listing the rule name and the offending entity reference expression string
- Given a canon_rules.yaml containing multiple independent errors (e.g. one rule with an unpropagated wildcard and another with a versionless tool reference), when the user runs `canon rules validate`, then all errors are collected and printed together before the command exits, rather than halting at the first error encountered
- Given a canon_rules.yaml containing multiple errors, when the user runs `canon rules validate`, then the command exits with a non-zero exit code and the total error count is included in the final summary line
- Given a canon_rules.yaml file that does not exist at the expected path, when the user runs `canon rules validate`, then the command exits with a non-zero exit code and prints an error message stating the file was not found along with the expected path
- Given a canon_rules.yaml that is syntactically invalid YAML, when the user runs `canon rules validate`, then the command exits with a non-zero exit code and prints a parse error message indicating the file could not be loaded

## Constraints
- Complexity: medium
