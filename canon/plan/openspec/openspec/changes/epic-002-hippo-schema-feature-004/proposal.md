# Define GeneAnnotation Entity Type

## Goal
Define GeneAnnotation Entity Type: Implement the GeneAnnotation entity type definition in schema.yaml with required fields including gene name and annotation source.

## Acceptance Criteria
- Given a researcher accesses the schema.yaml file, when they look for the GeneAnnotation entity type, then it is defined with gene_name and annotation_source fields of type string and required
- Given the schema validation tool runs on schema.yaml, when it processes the GeneAnnotation entity, then no type errors are reported and all fields are properly typed as string and required
- Given a database connection is established and a valid GeneAnnotation instance is created, when it is saved to the database, then all GeneAnnotation entity fields are stored correctly with proper string types

## Constraints
- Complexity: low
