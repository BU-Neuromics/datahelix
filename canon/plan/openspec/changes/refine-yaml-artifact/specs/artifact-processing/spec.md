## ADDED Requirements

### Requirement: YAML parsing and validation
The system SHALL validate all YAML artifacts before processing to ensure proper mapping syntax.

#### Scenario: Valid YAML artifact processed
- **WHEN** a valid YAML artifact is submitted
- **THEN** the system processes it without errors

#### Scenario: Invalid YAML artifact rejected
- **WHEN** an invalid YAML artifact is submitted
- **THEN** the system rejects it with a clear error message indicating the location of the issue

## MODIFIED Requirements

### Requirement: Artifact processing workflow
The system SHALL include mandatory YAML format validation as part of the artifact processing pipeline.

#### Scenario: Artifact with valid YAML accepted
- **WHEN** an artifact with correct YAML formatting is processed
- **THEN** the system accepts and continues processing

#### Scenario: Artifact with invalid YAML rejected
- **WHEN** an artifact with incorrect YAML formatting is processed
- **THEN** the system rejects it with a detailed error report