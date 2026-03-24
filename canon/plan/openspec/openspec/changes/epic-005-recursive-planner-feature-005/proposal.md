# 3-level dependency chain processing

## Goal
3-level dependency chain processing: Validates that RecursivePlanner correctly handles a 3-level dependency chain with mixed REUSE and BUILD decisions and wildcard threading.

## Acceptance Criteria
- Given a 3-level dependency chain FastqFile to TrimmedFastqFile to AlignmentFile where FastqFile and TrimmedFastqFile already exist in mock Hippo but AlignmentFile does not, when RecursivePlanner.resolve is called for AlignmentFile, then both required inputs return REUSE and only AlignmentFile triggers BUILD
- Given all 3 levels are missing from Hippo, when the planner resolves AlignmentFile, then it recursively resolves TrimmedFastqFile (which resolves FastqFile as REUSE), producing them in dependency order before executing the alignment CWL workflow
- Given a wildcard such as quality_cutoff is threaded across all 3 levels, when the planner resolves the top-level spec with quality_cutoff=20, then all 3 levels use quality_cutoff=20 in their Hippo queries and rule matches
- Given the 3-level chain is fully resolved, when the planner returns the top-level URI, then that URI matches the uri field on the newly ingested AlignmentFile entity in mock Hippo
- Given cycle detection is active, when the 3-level chain is resolved with no cycles, then no CanonCycleError is raised and the grey-set is empty after resolution completes

## Constraints
- Depends on: epic-005-recursive-planner-feature-001, epic-005-recursive-planner-feature-002, epic-005-recursive-planner-feature-003
- Complexity: medium
