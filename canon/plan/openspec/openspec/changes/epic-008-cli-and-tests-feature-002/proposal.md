# Canon Get Command Implementation

## Goal
Canon Get Command Implementation: Implement the canon get CLI command that resolves a single artifact spec to a URI using the full resolution pipeline.

## Acceptance Criteria
- Given a valid canon.yaml and a Hippo instance with a matching entity, when the user runs canon get AlignmentFile with the correct --param arguments, then the command prints the entity URI to stdout and exits with code 0
- Given no matching entity exists and a matching rule is found, when canon get is executed, then it resolves inputs recursively, executes the CWL workflow, ingests the output, and prints the resulting URI to stdout
- Given invalid --param syntax is passed to canon get, when the command executes, then it exits with a non-zero code and prints a message describing the expected format
- Given CanonNoRuleError is raised during resolution, when canon get handles it, then it exits with a non-zero code, prints the error message including available rules for the requested entity type, and does not produce a traceback
- Given CanonCycleError is raised, when canon get handles it, then it exits with a non-zero code and prints the full cycle path from the error

## Constraints
- Complexity: medium
