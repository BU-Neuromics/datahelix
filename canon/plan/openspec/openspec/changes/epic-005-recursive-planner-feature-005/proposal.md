# 3-level dependency chain processing

## Goal
3-level dependency chain processing: Validates that RecursivePlanner correctly handles a 3-level dependency chain with mixed REUSE and BUILD decisions and wildcard threading.

## Acceptance Criteria
- Given a 3-level dependency chain FastqFile → TrimmedFastqFile → AlignmentFile where FastqFile and TrimmedFastqFile already exist in mock Hippo but AlignmentFile does not, when RecursivePlanner.resolve is called with the AlignmentFile spec, then the resolution plan contains exactly two REUSE decisions (FastqFile, TrimmedFastqFile) and exactly one BUILD decision (AlignmentFile)
- Given the same partial-hit scenario, when the resolution plan is executed, then the BUILD step for AlignmentFile receives the existing URIs of FastqFile and TrimmedFastqFile as its resolved inputs and invokes the alignment CWL workflow exactly once
- Given all 3 levels (FastqFile, TrimmedFastqFile, AlignmentFile) are missing from mock Hippo, when RecursivePlanner.resolve is called for AlignmentFile, then the resolution plan contains three BUILD decisions ordered as FastqFile first, TrimmedFastqFile second, AlignmentFile third (dependency-topological order)
- Given the all-missing scenario, when the plan is executed, then each BUILD step completes and ingests its entity into mock Hippo before the next dependent step begins, and all three entities are queryable in Hippo after execution
- Given a wildcard parameter quality_cutoff=20 is defined at the top-level AlignmentFile spec, when the planner resolves the full 3-level chain, then the Hippo existence query for each level includes quality_cutoff=20 as a match field, and any BUILD-step rule evaluation receives quality_cutoff=20 in its input context
- Given quality_cutoff=30 is specified instead of 20 and entities exist in Hippo only for quality_cutoff=20, when the planner resolves the chain, then all three levels return BUILD (no false REUSE from mismatched parameter values)
- Given the 3-level chain is fully resolved and AlignmentFile is built, when the planner returns the top-level result, then the returned URI string equals the uri field on the AlignmentFile entity most recently ingested into mock Hippo, and that URI is a valid canon:// URI
- Given cycle detection is active and the 3-level chain contains no circular dependencies, when resolution completes successfully, then no CanonCycleError is raised, the internal grey-set (in-progress marker set) is empty, and every node in the dependency graph is in the black-set (fully resolved)
- Given cycle detection is active and a synthetic cycle is injected (AlignmentFile depends on FastqFile which depends on AlignmentFile), when RecursivePlanner.resolve is called, then a CanonCycleError is raised before any BUILD step executes, and the error message identifies the cycle participants

## Constraints
- Depends on: epic-005-recursive-planner-feature-001, epic-005-recursive-planner-feature-002, epic-005-recursive-planner-feature-003
- Complexity: medium
