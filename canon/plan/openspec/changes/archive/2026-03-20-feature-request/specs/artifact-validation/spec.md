## ADDED Requirements

### Requirement: YAML validation layer
The system SHALL include a validation layer that checks YAML syntax in artifact files before processing.

#### Scenario: Valid YAML passes validation
- **WHEN** an artifact with valid YAML is processed
- **THEN** the artifact is processed normally without errors

#### Scenario: Invalid YAML fails validation
- **WHEN** an artifact with invalid YAML syntax is processed
- **THEN** system reports a clear error message indicating the file, line number, and parsing issue