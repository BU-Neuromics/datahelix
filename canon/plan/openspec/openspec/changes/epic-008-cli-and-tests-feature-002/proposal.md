# Canon Get Command Implementation

## Goal
Canon Get Command Implementation: Implement the canon get CLI command that resolves a single artifact spec to a URI using the full resolution pipeline.

## Acceptance Criteria
- Given a valid canon.yaml is loaded and a Hippo instance contains an entity of type AlignmentFile whose parameters match the supplied --param arguments, when the user runs `canon get AlignmentFile --param sample=S1 --param ref_genome=hg38`, then the command prints exactly one URI (e.g. hippo://alignmentfile/abc123) to stdout on a single line and the process exits with code 0
- Given a valid canon.yaml is loaded and no matching entity exists in Hippo but a rule producing AlignmentFile is defined in canon_rules.yaml, when the user runs `canon get AlignmentFile --param sample=S1 --param ref_genome=hg38`, then the resolver recursively resolves all input dependencies, executes the CWL workflow specified by the matching rule, ingests the output into Hippo, prints the resulting URI to stdout, and exits with code 0
- Given a rule's input dependencies themselves require resolution (two or more levels deep), when `canon get` is run for the top-level entity type, then each intermediate dependency is resolved in the correct topological order before the final workflow executes, and the final URI is printed to stdout with exit code 0
- Given the user passes a --param flag with invalid syntax (e.g. `--param sample`, `--param =value`, or `--param`), when the command executes, then it exits with a non-zero exit code, prints a human-readable error message to stderr that describes the expected `key=value` format, and does not print a URI to stdout
- Given the user passes a --param key that is not declared in the entity type's parameter schema, when the command executes, then it exits with a non-zero exit code and prints an error to stderr listing the valid parameter names for that entity type
- Given no rule in canon_rules.yaml can produce the requested entity type and no matching entity exists in Hippo (CanonNoRuleError), when `canon get` handles the error, then it exits with a non-zero exit code, prints an error message to stderr that names the requested entity type and lists available rules (if any) for related types, and does not produce a Python traceback on stderr
- Given a circular dependency is detected during recursive resolution (CanonCycleError), when `canon get` handles the error, then it exits with a non-zero exit code and prints the full cycle path (e.g. "A -> B -> C -> A") to stderr without a Python traceback
- Given the user runs `canon get` without specifying an entity type argument, when the command executes, then it exits with a non-zero exit code and prints a usage message to stderr that includes the expected invocation syntax
- Given a required --param argument is omitted for an entity type that requires it, when the command executes, then it exits with a non-zero exit code and prints an error to stderr identifying which required parameters are missing

## Constraints
- Complexity: medium
