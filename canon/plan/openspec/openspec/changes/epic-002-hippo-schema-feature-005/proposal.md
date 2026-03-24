# Define WorkflowRun Entity Type

## Goal
Define WorkflowRun Entity Type: Implement the WorkflowRun entity type definition in schema.yaml with required fields including workflow name and execution timestamp.

## Acceptance Criteria
- Given a researcher accesses the schema.yaml file, when they look for the WorkflowRun entity type, then it is defined with workflow name and execution timestamp fields
- Given the schema is validated, when it passes validation checks, then all WorkflowRun entity fields are properly typed and required
- Given a new WorkflowRun instance is created, when it is saved to the database, then all WorkflowRun entity fields are stored correctly
- Given the schema.yaml file contains the WorkflowRun entity definition, when a validator tool runs against it, then no validation errors are returned
- Given a researcher queries the schema documentation, when they search for WorkflowRun entity fields, then workflow name and execution timestamp fields are clearly documented
- Given a new WorkflowRun instance is created with valid data, when it is saved to the database, then the workflow name field stores string values correctly
- Given a new WorkflowRun instance is created with valid data, when it is saved to the database, then the execution timestamp field stores date-time values correctly
- Given an invalid WorkflowRun instance is created, when it tries to save to the database, then a validation error is thrown
- Given the WorkflowRun entity definition exists in schema.yaml, when a data model generator processes it, then the generated model includes workflow name and execution timestamp fields
- Given a researcher examines the schema.yaml file directly, when they look for WorkflowRun entity definitions, then the entity is defined with proper YAML structure and field declarations

## Constraints
- Complexity: low
