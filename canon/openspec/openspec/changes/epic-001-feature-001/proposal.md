# CanonConfig and CanonError hierarchy

## Goal
CanonConfig and CanonError hierarchy: Define the top-level CanonConfig pydantic model (hippo_url, executor, rules_file, work_dir) and the Canon exception hierarchy (CanonError, CanonPlanningError, CanonCycleError, CanonValidationError, CanonExecutorError, CanonIngestionError). Config is loadable from a YAML file and validated on construction.

## Acceptance Criteria
- Given a valid canon.yaml file with all required fields, when CanonConfig.from_yaml() is called, then it loads without errors and all fields (hippo_url, executor, rules_file, work_dir) are accessible and correctly populated
- Given a canon.yaml file missing the executor field, when CanonConfig.from_yaml() is called, then it raises a CanonValidationError with a descriptive message indicating the missing required field
- Given a canon.yaml file with an invalid executor name, when CanonConfig.from_yaml() is called, then it raises a CanonValidationError with a descriptive message indicating the invalid executor value
- Given the canonical exception module structure, when importing from canon.exceptions, then all Canon exception types (CanonError, CanonPlanningError, CanonCycleError, CanonValidationError, CanonExecutorError, CanonIngestionError) are importable and inherit from CanonError
- Given a canon.yaml file with valid content, when CanonConfig.from_yaml() is called, then it returns a valid CanonConfig instance that can be used for further processing without validation errors

## Constraints
- Complexity: low
