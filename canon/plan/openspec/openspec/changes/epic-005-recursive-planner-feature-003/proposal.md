# Wildcard binding logic

## Goal
Wildcard binding logic: Implement wildcard binding logic in RecursivePlanner to bind rule wildcard parameters to concrete values from the request spec and propagate them through the dependency chain.

## Acceptance Criteria
- Given a canon rule with wildcard parameters in its produces.match block, when the planner receives a request spec with concrete values for those wildcards, then bind_wildcards returns a dict mapping each wildcard name to its bound concrete value
- Given a requires.match block using the same wildcard name as in produces.match, when substitute_wildcards is called with the bound values, then the wildcard in requires is replaced with the concrete value from the request
- Given a request spec that is missing a wildcard that appears in produces.match, when bind_wildcards is called, then it raises CanonPlanningError with the missing wildcard name in the message
- Given a rule with wildcards nested inside entity ref expressions such as ref:GenomeBuild{name={genome_build}}, when the wildcard is bound to GRCh38, then the entity ref becomes ref:GenomeBuild{name=GRCh38} before resolution
- Given a 3-rule chain where a wildcard is threaded from trim_reads through align_reads to count_genes, when the top-level request binds the wildcard, then all three rules resolve using the same bound value

## Constraints
- Complexity: medium
