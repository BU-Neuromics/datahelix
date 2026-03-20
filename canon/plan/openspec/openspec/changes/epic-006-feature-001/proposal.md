# canon_outputs.json ingestion into Hippo

## Goal
canon_outputs.json ingestion into Hippo: Implement OutputIngestionPipeline that reads canon_outputs.json from the workflow work directory after successful execution. Validates the JSON structure as a Hippo batch ingest payload (list of entity dicts with entity_type and metadata fields). POSTs to the Hippo batch ingest endpoint. Returns a list of ingested entity IDs. Raises CanonIngestionError with details for any ingestion failures.

## Acceptance Criteria
- Given a valid work directory containing .canon_outputs.json file, when OutputIngestionPipeline.ingest() is called, then it reads the JSON file and returns a list of 2 entity IDs
- Given a work directory with malformed canon_outputs.json (not a list structure), when OutputIngestionPipeline.ingest() is called, then it raises CanonIngestionError before making any HTTP calls
- Given a Hippo service returning a 4xx HTTP status during ingest, when OutputIngestionPipeline.ingest() is called with valid data, then it raises CanonIngestionError including the HTTP status code and response body
- Given a canon_outputs.json with entities missing entity_type field, when OutputIngestionPipeline.ingest() is called, then it raises CanonIngestionError before any HTTP calls
- Given a canon_outputs.json with entities missing metadata field, when OutputIngestionPipeline.ingest() is called, then it raises CanonIngestionError before any HTTP calls

## Constraints
- Depends on: epic-003-feature-001, epic-005-feature-001
- Complexity: medium
