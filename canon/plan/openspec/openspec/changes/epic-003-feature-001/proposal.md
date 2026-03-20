# HippoClient — entity query by type and metadata filter

## Goal
HippoClient — entity query by type and metadata filter: Implement HippoClient that wraps the Hippo REST API and provides query_entities( entity_type, metadata_filter) returning a list of entity dicts matching the type and all metadata key-value pairs. Also provides get_entity(entity_id) for retrieving a single entity by ID. Uses bearer token authentication from CanonConfig.


## Acceptance Criteria
- HippoClient.query_entities("AlignmentFile", {"sample_id": "S001", "aligner": "STAR"}) returns entities matching all filters
- HippoClient.query_entities with no matching entities returns an empty list
- HippoClient.get_entity(entity_id) returns the entity dict or raises CanonValidationError if not found
- HippoClient raises CanonExecutorError with status code on HTTP 4xx/5xx responses
- HippoClient is constructable from CanonConfig (reads hippo_url and auth token)
- All HTTP calls include the Authorization: Bearer <token> header if auth_token is set

## Constraints
- Depends on: epic-001-feature-001
- Complexity: medium
