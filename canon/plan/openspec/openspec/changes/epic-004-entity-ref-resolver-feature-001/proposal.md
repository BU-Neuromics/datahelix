# EntityRefResolver with UUID lookup

## Goal
EntityRefResolver with UUID lookup: Implement the EntityRefResolver that can parse entity reference expressions and perform UUID lookups for entities in Hippo.

## Acceptance Criteria
- Given a valid entity reference string "sample/SAM-001", when EntityRefResolver.resolve() is called, then it returns a Hippo UUID string matching the regex pattern "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
- Given an entity reference string missing the "/" delimiter (e.g. "sampleSAM-001"), when EntityRefResolver.resolve() is called, then it raises CanonResolutionError with error code "MALFORMED_REFERENCE" and a message containing the offending input string
- Given an entity reference with an unknown entity type (e.g. "unknown_type/SAM-001") where "unknown_type" is not in the set of registered Hippo entity types, when EntityRefResolver.resolve() is called, then it raises CanonResolutionError with error code "UNKNOWN_ENTITY_TYPE" and a message listing the valid entity types
- Given a valid entity reference "sample/nonexistent-id" where the entityId does not exist in Hippo, when EntityRefResolver.resolve() is called, then it raises CanonResolutionError with error code "ENTITY_NOT_FOUND" and a message containing both the entity type and the entityId that was not found
- Given an empty string "", a None value, or a whitespace-only string "   ", when EntityRefResolver.resolve() is called, then it raises CanonResolutionError with error code "EMPTY_REFERENCE" before any Hippo lookup is attempted
- Given an entity reference containing special characters in the entityId (e.g. "sample/SAM-001_v2.3" or "sample/SAM:001"), when EntityRefResolver.resolve() is called, then it resolves successfully and returns the corresponding Hippo UUID without escaping or modifying the entityId
- Given an entity reference string exceeding 512 characters in total length, when EntityRefResolver.resolve() is called, then it raises CanonResolutionError with error code "REFERENCE_TOO_LONG" and a message stating the maximum allowed length of 512 characters
- Given a valid entity reference "sample/SAM-001", when EntityRefResolver.resolve() is called and the Hippo lookup service is unreachable, then it raises CanonResolutionError with error code "LOOKUP_FAILED" and a message indicating the upstream service is unavailable, rather than an unhandled connection exception

## Constraints
- Complexity: medium
