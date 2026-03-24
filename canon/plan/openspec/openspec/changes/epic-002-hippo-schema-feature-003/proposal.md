# Define GenomeBuild Entity Type

## Goal
Define GenomeBuild Entity Type: Implement the GenomeBuild entity type definition in schema.yaml with required fields including genome assembly and build date.

## Acceptance Criteria
- Given a researcher accesses the schema.yaml file, when they look for the GenomeBuild entity type, then it is defined with genome assembly and build date fields of correct types and required attributes
- Given the schema.yaml file is parsed, when it contains GenomeBuild entity definition, then the genome assembly field is of string type and required
- Given the schema.yaml file is parsed, when it contains GenomeBuild entity definition, then the build date field is of date type and required

## Constraints
- Complexity: low
