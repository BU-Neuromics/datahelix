# ValueResolver types

## Goal
ValueResolver types: Define the four ValueResolver types (URIResolver, FieldResolver, InlineResolver, JSONResolver) as a discriminated union. Each resolver takes a binding name and an entity dict, and returns the resolved string value. URIResolver returns the entity's uri field; FieldResolver returns an arbitrary named field; InlineResolver returns a static string constant; JSONResolver returns the full entity serialized as JSON.


## Acceptance Criteria
- URIResolver("fastq_r1").resolve(entity) returns entity["uri"]
- FieldResolver("fastq_r1", "sample_id").resolve(entity) returns entity["sample_id"]
- InlineResolver("hg38").resolve(entity) returns "hg38" regardless of entity content
- JSONResolver("star_index").resolve(entity) returns a valid JSON string of the entity dict
- Resolver type is inferred from the placeholder syntax: {binding.uri}, {binding.field_name}, {binding.json}, or static string
- A missing field in FieldResolver raises CanonValidationError with the field name

## Constraints
- Depends on: epic-001-feature-002
- Complexity: low
