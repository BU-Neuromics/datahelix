## ADDED Requirements

### Requirement: YAML formatting guidelines
The system SHALL provide comprehensive YAML formatting guidelines for all OpenSpec artifact files.

#### Scenario: Developer follows formatting guidelines
- **WHEN** a developer creates artifacts following the YAML formatting guidelines
- **THEN** the artifacts can be processed without YAML parsing errors

#### Scenario: Developer violates formatting guidelines
- **WHEN** a developer creates artifacts with invalid YAML syntax
- **THEN** system provides clear error messages pointing to the specific issues