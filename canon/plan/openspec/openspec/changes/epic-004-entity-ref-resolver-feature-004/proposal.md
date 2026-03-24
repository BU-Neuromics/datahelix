# Find entity operations in HippoQueryClient

## Goal
Find entity operations in HippoQueryClient: Implement find_entity and find_entities methods for retrieving entities from Hippo.

## Acceptance Criteria
- Given a valid entity UUID, when the client calls find_entity with that UUID, then it returns a JSON object containing the entity data with all expected fields
- Given multiple valid entity IDs, when the client calls find_entities with those IDs, then it returns a list of entity data objects matching the provided IDs in the same order
- Given an invalid entity ID format (non-UUID string), when the client calls find_entity, then it raises CanonResolutionError with error code "INVALID_UUID"
- Given an entity UUID that does not exist in Hippo database, when the client calls find_entity, then it raises CanonResolutionError with error code "ENTITY_NOT_FOUND"
- Given a list of entity IDs containing one or more invalid IDs, when the client calls find_entities, then it returns a list where valid entities are included and invalid IDs result in null values at corresponding positions
- Given an empty list of entity IDs, when the client calls find_entities, then it returns an empty list
- Given a valid UUID string with correct format but no corresponding entity, when the client calls find_entity, then it raises CanonResolutionError with error code "ENTITY_NOT_FOUND"
- Given a valid entity UUID, when the client calls find_entity multiple times, then each call returns the same entity data object

## Constraints
- Depends on: feature-003
- Complexity: medium
