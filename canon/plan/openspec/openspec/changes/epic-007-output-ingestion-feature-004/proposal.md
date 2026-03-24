# CWL Output Parsing and Entity POST Service

## Goal
CWL Output Parsing and Entity POST Service: Implement the full OutputIngestionPipeline that parses CWL output JSON, applies sidecar field mappings, and POSTs entities to the Hippo REST API.

## Acceptance Criteria
- Given a CWL run that produced a valid JSON output object and a sidecar with hippo_fields expressions mapping CWL outputs to Hippo entity fields, when OutputIngestionPipeline.process() is called with that output JSON and sidecar, then it returns a result containing the UUID of the created Hippo entity and the HTTP response status is 201
- Given the sidecar defines hippo_fields expressions that reference nested CWL output values (e.g. "outputs.alignment.bam_path"), when the pipeline evaluates those expressions against the CWL output JSON, then each resolved value matches the corresponding value at that JSON path and all resolved values appear in the constructed entity payload
- Given the sidecar declares identity_fields of ["sample", "genome_build", "aligner"] and the CWL inputs contain values for each, when the pipeline constructs the entity payload and POSTs it to Hippo, then the request body includes exactly those three fields with values matching the original CWL inputs
- Given Hippo returns HTTP 422 with an error body containing a "detail" field, when OutputIngestionPipeline handles the response, then it raises CanonIngestionError whose message includes the string "422" and the full Hippo error detail text
- Given Hippo returns HTTP 500 or any other 5xx status, when OutputIngestionPipeline handles the response, then it raises CanonIngestionError with the HTTP status code and does not retry by default
- Given a CWL output JSON that is missing a field declared with optional=false in the sidecar, when the pipeline validates outputs against the sidecar schema, then it raises CanonIngestionError whose message identifies the missing field name and states it is required
- Given a CWL output JSON where multiple required fields are missing, when the pipeline validates outputs, then the raised CanonIngestionError message identifies all missing required field names, not just the first one encountered
- Given a CWL output JSON where an output declared with optional=true in the sidecar is absent, when the pipeline processes that output, then it skips entity creation for that output, logs a debug-level message noting the skip, and does not raise an error
- Given a CWL output JSON containing a field whose value type does not match the type declared in the sidecar (e.g. string where integer expected), when the pipeline validates the output, then it raises CanonIngestionError identifying the field name, expected type, and actual type
- Given a sidecar with hippo_fields expressions and a CWL output JSON, when the pipeline constructs the entity payload, then the POST request to Hippo uses Content-Type application/json, targets the endpoint specified in the sidecar's entity_type configuration, and includes the Authorization header from the pipeline's configured credentials

## Constraints
- Complexity: high
