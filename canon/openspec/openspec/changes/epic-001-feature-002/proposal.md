# ProductionRule and WildcardBinding models

## Goal
ProductionRule and WildcardBinding models: Define the ProductionRule pydantic model with produces (entity_type + metadata dict with wildcard placeholders), requires (list of InputBinding with bind/entity_type/metadata), and execute (workflow identifier + inputs dict + outputs list) sections. WildcardBinding maps wildcard names to resolved string values. Wildcards are denoted {name} in metadata values.


## Acceptance Criteria
- ProductionRule loads from a valid rule dict with all required fields
- Wildcard placeholders in metadata values are detected and extracted as a set of names
- A rule with missing produces.entity_type raises CanonValidationError
- InputBinding requires bind, entity_type, and metadata fields
- WildcardBinding is a typed dict-like container supporting get/set by name
- ProductionRule.wildcard_names property returns the union of all wildcard placeholder names across produces and requires

## Constraints
- Depends on: epic-001-feature-001
- Complexity: medium
