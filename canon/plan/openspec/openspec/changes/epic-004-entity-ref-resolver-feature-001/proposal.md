# EntityRefResolver with UUID lookup

## Goal
EntityRefResolver with UUID lookup: Implement the EntityRefResolver that can parse entity reference expressions and perform UUID lookups for entities in Hippo.

## Acceptance Criteria
- Given a valid entity reference expression in the format "entityType/entityId", when the resolver processes it, then it successfully resolves to a valid Hippo UUID
- Given an invalid entity reference expression with missing delimiter, when the resolver attempts to process it, then it raises CanonResolutionError with appropriate error message indicating malformed reference
- Given an invalid entity reference expression with invalid entity type, when the resolver attempts to process it, then it raises CanonResolutionError with appropriate error message indicating unknown entity type
- Given a valid entity reference expression for a non-existent entity UUID, when the resolver looks it up, then it raises CanonResolutionError indicating entity not found
- Given an empty or null entity reference expression, when the resolver attempts to process it, then it raises CanonResolutionError with appropriate error message indicating null or empty reference
- Given a valid entity reference expression with special characters in entityId, when the resolver processes it, then it successfully resolves to a valid Hippo UUID
- Given an entity reference expression that exceeds maximum length limit, when the resolver attempts to process it, then it raises CanonResolutionError with appropriate error message indicating reference too long
- Given a valid entity reference expression with valid entityType and entityId, when the resolver looks up the UUID in Hippo, then it returns the expected UUID string with proper format

## Constraints
- Complexity: medium
