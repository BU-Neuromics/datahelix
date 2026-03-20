# ProductionRule and WildcardBinding models

## Goal
ProductionRule and WildcardBinding models: Define the ProductionRule pydantic model with produces (entity_type + metadata dict with wildcard placeholders), requires (list of InputBinding with bind/entity_type/metadata), and execute (workflow identifier + inputs dict + outputs list) sections. WildcardBinding maps wildcard names to resolved string values. Wildcards are denoted {name} in metadata values.


## Acceptance Criteria
- Given a valid rule dictionary with all required fields, when ProductionRule is instantiated, then it successfully loads without validation errors
- Given a rule dictionary containing wildcard placeholders in metadata values, when ProductionRule processes the metadata, then it detects and extracts all wildcard placeholder names as a set of unique names
- Given a rule dictionary missing the produces.entity_type field, when ProductionRule is instantiated, then it raises a CanonValidationError with appropriate error message
- Given an InputBinding without required bind, entity_type, or metadata fields, when ProductionRule validates the binding, then it raises a validation error for each missing field
- Given a WildcardBinding instance, when values are set and retrieved by name, then it supports get/set operations similar to a typed dict-like container
- Given a ProductionRule with wildcard placeholders in both produces and requires sections, when wildcard_names property is accessed, then it returns the union of all wildcard placeholder names across both sections as a single set
- Given a rule dictionary with multiple identical wildcard names in metadata values, when wildcard names are extracted, then it returns a set containing only unique wildcard names
- Given a rule dictionary with no wildcard placeholders in metadata values, when wildcard names are extracted, then it returns an empty set
- Given a complex nested metadata structure with wildcard placeholders, when wildcards are detected, then it extracts all wildcard names from all levels of nesting
- Given a rule dictionary with malformed wildcard syntax (e.g., {name without closing brace), when ProductionRule processes the metadata, then it raises appropriate validation error for invalid wildcard format

## Constraints
- Depends on: epic-001-feature-001
- Complexity: medium
