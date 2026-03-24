# Model Integration Testing

## Goal
Model Integration Testing: Create unit tests for all Pydantic models and exception classes with comprehensive coverage.

## Acceptance Criteria
- Given a valid YAML configuration file containing all required fields with correct types, when CanonConfig.from_yaml() loads the content, then all model properties are initialized with the expected values and model_validate() raises no ValidationError
- Given a YAML configuration missing a required field (e.g., 'name' omitted from a model that requires it), when CanonConfig.from_yaml() is called, then a Pydantic ValidationError is raised whose errors() list contains an entry with type 'missing' and the loc tuple identifying the missing field
- Given a YAML configuration where a field has the wrong type (e.g., a string where an int is expected), when CanonConfig.from_yaml() is called, then a Pydantic ValidationError is raised whose errors() list contains an entry with a type indicating the type mismatch and the loc tuple identifying the offending field
- Given a YAML configuration containing an extra key not defined in the model schema, when CanonConfig.from_yaml() is called with models configured as model_config = ConfigDict(extra='forbid'), then a Pydantic ValidationError is raised with an 'extra_forbidden' error type for the unexpected field
- Given a YAML configuration with nested object structures (e.g., a parent model containing child model fields), when CanonConfig.from_yaml() loads the content, then the nested child models are correctly instantiated and their properties match the YAML values
- Given a YAML configuration that omits optional fields which have default values defined in the model, when CanonConfig.from_yaml() loads the content, then those fields are populated with their declared default values
- Given empty string input or None passed as YAML content, when CanonConfig.from_yaml() is called, then a ValueError is raised with a message indicating that the input content is empty or null
- Given syntactically invalid YAML content (e.g., unmatched brackets, bad indentation), when CanonConfig.from_yaml() attempts to parse it, then a yaml.YAMLError is raised before any Pydantic validation occurs
- Given the complete test suite for all Pydantic model classes and exception classes, when pytest is run with --cov targeting the models module, then line coverage is at least 95% and every public method and validator on each model class is exercised by at least one test
- Given each custom exception class defined in the codebase, when a test instantiates the exception with representative arguments and raises it, then the exception message, attributes, and inheritance chain match their documented contract

## Constraints
- Depends on: feature-001, feature-002, feature-003
- Complexity: high
