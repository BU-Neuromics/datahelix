# CWL Output Parsing and Entity POST Service

## Goal
CWL Output Parsing and Entity POST Service: Implement the full OutputIngestionPipeline that parses CWL output JSON, applies sidecar field mappings, and POSTs entities to the Hippo REST API.

## Acceptance Criteria
- Given a successful CWL run returning a JSON output object, when OutputIngestionPipeline processes it, then it parses the JSON, evaluates the sidecar hippo_fields expressions, constructs the entity payload, and POSTs to Hippo returning the created entity UUID
- Given the sidecar declares identity_fields of sample, genome_build, and aligner, when the entity is POSTed to Hippo, then those three fields are present in the request body and match the values from the CWL inputs
- Given Hippo returns HTTP 422 for an entity POST, when OutputIngestionPipeline handles the response, then it raises CanonIngestionError with the HTTP status and Hippo error body in the message
- Given a CWL output JSON that is missing a field declared as optional=false in the sidecar, when the pipeline processes it, then CanonIngestionError is raised identifying the missing required output
- Given a CWL output JSON with an optional output field where optional=true in the sidecar, when that output is absent from the JSON, then the pipeline skips it without error and does not create a Hippo entity for that output

## Constraints
- Complexity: high
