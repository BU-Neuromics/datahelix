# Ingest entity operations in HippoQueryClient

## Goal
Ingest entity operations in HippoQueryClient: Implement ingest_entity method for creating and updating entities in Hippo.

## Acceptance Criteria
- Given valid entity data with all required fields (entity_type, fields dict, and optional metadata) and no UUID provided, when the client calls ingest_entity, then it creates a new entity in Hippo, generates a v4 UUID, and returns a response object containing that UUID with HTTP 201 status
- Given valid entity data that includes a UUID matching an existing entity of the same entity_type, when the client calls ingest_entity, then it replaces all mutable fields on the existing entity with the new values (full replace, not merge), preserves the original UUID and created_at timestamp, updates the updated_at timestamp, and returns a response containing the same UUID with HTTP 200 status
- Given entity data missing one or more required fields (e.g., entity_type is null or fields dict is absent), when the client calls ingest_entity, then it raises a ValidationException whose message lists each missing field by name, does not persist any data to Hippo, and does not generate a UUID
- Given entity data where field values violate type constraints (e.g., string where int expected, negative value for a positive-only field, or ISO-8601 date in wrong format), when the client calls ingest_entity, then it raises a ValidationException whose message identifies each offending field name, the expected type, and the actual value provided
- Given entity data containing a string field whose value exceeds the configured maximum length for that field, when the client calls ingest_entity, then it raises a ValidationException specifying the field name, the maximum allowed length, and the actual length provided
- Given a client constructed with invalid or expired authentication credentials, when the client calls ingest_entity with otherwise valid entity data, then it raises an AuthenticationException before any validation or persistence occurs, and no entity is created or modified in Hippo
- Given valid entity data but the Hippo service is unreachable (network timeout or connection refused), when the client calls ingest_entity, then it raises a NetworkException that includes the target host, port, and a human-readable description of the failure, within the configured timeout period
- Given entity data with a caller-supplied UUID that does not match any existing entity, when the client calls ingest_entity, then it creates a new entity using the caller-supplied UUID (not a generated one) and returns a response containing that exact UUID with HTTP 201 status
- Given a concurrent update scenario where two ingest_entity calls target the same existing entity UUID simultaneously, when both calls execute, then exactly one succeeds and the other raises a ConflictException (HTTP 409), ensuring no silent data loss from last-write-wins behavior
- Given valid entity data referencing a dependent entity via a foreign-key relationship field, when the referenced entity does not exist in Hippo, then ingest_entity raises a ValidationException indicating the referenced entity UUID was not found, and no partial write occurs

## Constraints
- Depends on: feature-003
- Complexity: medium
