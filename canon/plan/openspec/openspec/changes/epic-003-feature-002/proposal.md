# Wildcard binding resolution

## Goal
Wildcard binding resolution: Implement wildcard binding resolution: given a metadata request spec (possibly with wildcard values from the CLI) and a set of resolved input entities, extract and bind all wildcard placeholders. Required wildcards without a source (neither from the request spec nor derivable from an input entity field) raise CanonPlanningError. Wildcard values derived from input entities propagate to dependent rules.


## Acceptance Criteria
- Given request spec {sample_id: "S001"} and rule with {sample_id} placeholder, WildcardBinding["sample_id"] == "S001"
- Given a rule with {genome_build} bound from a resolved StarIndex entity genome_build field, binding resolves correctly
- Given a required wildcard with no source, CanonPlanningError is raised naming the unbound wildcard and the rule
- Wildcard values from the request spec take precedence over values derived from input entities
- resolve_wildcards(rule, request_spec, input_entities) returns a complete WildcardBinding or raises

## Constraints
- Depends on: epic-001-feature-002, epic-003-feature-001
- Complexity: medium
