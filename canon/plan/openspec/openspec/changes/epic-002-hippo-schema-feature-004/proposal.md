# Define GeneAnnotation Entity Type

## Goal
Define GeneAnnotation Entity Type: Implement the GeneAnnotation entity type definition in schema.yaml with required fields including gene name and annotation source.

## Acceptance Criteria
- Given the schema.yaml file exists, when a developer inspects the entity definitions, then a GeneAnnotation entity type is present as a top-level class
- Given the GeneAnnotation entity is defined in schema.yaml, when its fields are inspected, then a gene_name field of type string is present and marked as required
- Given the GeneAnnotation entity is defined in schema.yaml, when its fields are inspected, then an annotation_source field of type string is present and marked as required
- Given schema.yaml contains the GeneAnnotation entity, when the LinkML schema validator is run against the file, then validation passes with zero errors for the GeneAnnotation class
- Given a valid GeneAnnotation instance with gene_name and annotation_source values, when the instance is persisted to the database via the SDK, then the record is stored with correct string types and can be retrieved with matching field values
- Given a GeneAnnotation instance is created with gene_name or annotation_source omitted, when validation runs, then a required-field validation error is raised before persistence

## Constraints
- Complexity: low
