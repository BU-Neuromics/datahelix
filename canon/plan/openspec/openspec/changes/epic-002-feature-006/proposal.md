# WorkflowRun Entity Schema Definition

## Goal
WorkflowRun Entity Schema Definition: Define the LinkML schema for the WorkflowRun entity type with required fields and validation rules, specifically capturing rule_name, cwl_workflow_hash, cwl_runner_version, execution_environment, input_entities, output_entity_id, and status fields.

## Acceptance Criteria
- Given a LinkML schema defining the WorkflowRun class, when the schema is loaded and inspected, then it must declare exactly these seven slots as required — rule_name, cwl_workflow_hash, cwl_runner_version, execution_environment, input_entities, output_entity_id, and status — each with an explicit range (data type) annotation
- Given a valid JSON/YAML instance containing all seven required fields with conforming values, when validated against the WorkflowRun LinkML schema, then validation passes with zero errors and the instance round-trips without data loss
- Given a JSON/YAML instance missing the rule_name field, when validated against the WorkflowRun schema, then validation fails and the error output contains the substring "rule_name" and indicates it is a required field
- Given a JSON/YAML instance missing the cwl_workflow_hash field, when validated against the WorkflowRun schema, then validation fails and the error output contains the substring "cwl_workflow_hash" and indicates it is a required field
- Given a JSON/YAML instance missing three or more required fields (e.g., cwl_runner_version, execution_environment, and status), when validated against the WorkflowRun schema, then the validator reports each missing field individually in a single validation pass rather than stopping at the first error
- Given the WorkflowRun schema is compiled to a Python dataclass or Pydantic model via LinkML gen-python, when a caller instantiates WorkflowRun omitting any single required field, then a TypeError or ValidationError is raised at construction time before any persistence call
- Given a WorkflowRun instance with all required fields populated, when the input_entities field value is not a list of entity references (e.g., a bare string or an integer), then schema validation rejects the value with an error identifying the expected type (multivalued entity reference)
- Given the compiled LinkML schema artifact, when queried for the WorkflowRun class definition via schema introspection or the generated JSON Schema, then the response lists all seven fields under the "required" key with their declared types matching the design spec (string for rule_name, string for cwl_workflow_hash, string for cwl_runner_version, string for execution_environment, array of entity references for input_entities, entity reference for output_entity_id, enum or string for status)

## Constraints
- Depends on: feature-001
- Complexity: medium
