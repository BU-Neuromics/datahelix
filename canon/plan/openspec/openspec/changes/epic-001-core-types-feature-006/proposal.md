# Full type-safe configuration system integration

## Goal
Full type-safe configuration system integration: Integrate all core types, config loading, and exception handling into a complete, testable configuration system.

## Acceptance Criteria
- Given a canon.yaml containing a CanonSpec with ScalarParam fields of types int, str, float, and bool (e.g., threshold: 42, label: "high", rate: 3.14, enabled: true), when CanonConfig loads the file and constructs CanonSpec instances with their parameter dataclasses, then each ScalarParam.value has the correct Python type (isinstance checks pass for int, str, float, bool respectively) and ScalarParam.param_type equals "scalar" for every parameter

- Given a canon.yaml containing a CanonSpec with EntityRefParam fields referencing entities (e.g., owner: "user:alice", sample: "sample:ABC-123"), when CanonConfig loads the file and constructs the parameter objects, then each EntityRefParam correctly parses entity_type and entity_id (e.g., entity_type="user", entity_id="alice"), and ResolvedInput can resolve these references to typed entity objects without raising exceptions

- Given a canon.yaml containing a CanonSpec with nested structures (a dict field containing sub-dicts, and a List[SubSpec] field where SubSpec has its own typed fields), when CanonConfig loads the file and validates the full object graph, then nested dict values preserve their Python types through the parse, SubSpec instances within lists each pass their own field-level validation, and the complete structure round-trips through yaml.dump/yaml.safe_load with structural equality

- Given a canon.yaml where a ScalarParam intended as int contains the string "not_a_number" and an EntityRefParam contains reference "missing-colon-format", when CanonConfig loads and validates, then the exception hierarchy activates correctly: a CanonConfigError is raised whose 'errors' list contains at least two entries — one with a field dot-path to the int field citing the type mismatch, and one citing the invalid entity reference format — and isinstance(error, CanonError) returns True

- Given a canon.yaml missing two required fields (one required ScalarParam with no default, one required EntityRefParam), when CanonConfig loads and validates, then a CanonConfigError is raised whose 'errors' list has length >= 2 where each entry contains the 'field' name of the missing parameter and a 'message' describing it as required, and no other fields are affected by the missing values

- Given a canon.yaml with optional fields that declare default values (e.g., retries defaults to 3, mode defaults to "DRAFT" from enum ["DRAFT", "ACTIVE", "DEPRECATED"]), when CanonConfig loads a file omitting those fields, then CanonSpec instances contain the declared defaults with correct types (retries is int 3, mode is str "DRAFT"), and when mode is set to invalid enum value "UNKNOWN", then a ValueError is raised listing the valid options

- Given a canon.yaml with environment variable interpolation (e.g., output_dir: "${OUTPUT_DIR}") and OUTPUT_DIR is set to "/data/results" in the environment, when CanonConfig loads the file, then the resolved value is the string "/data/results"; and when the environment variable is unset and no default is declared, then a CanonConfigError is raised indicating the unresolvable variable name

- Given a canon.yaml containing rules where ruleA depends on ruleB and ruleB depends on ruleA (circular dependency), when CanonConfig loads and resolves dependencies, then a CanonCycleError is raised whose 'cycle' field contains the circular path, and isinstance(error, CanonResolutionError) and isinstance(error, CanonError) both return True, confirming the full exception hierarchy

- Given a valid canon.yaml that exercises all integrated components (CanonConfig loading, CanonSpec with mixed ScalarParam/EntityRefParam/WildcardParam fields, default values, enum constraints, and pattern constraints), when the complete object is serialized to JSON via to_dict()/json.dumps and deserialized back, then the round-tripped data is structurally equal to the original with identical Python types, and WildcardParam.match() still functions correctly on the deserialized instance (e.g., pattern "sample_*_v[0-9]" matches "sample_RNA_v3" and rejects "experiment_RNA_v3")

- Given a valid canon.yaml with all supported parameter types, when a complete integration test suite runs covering: (1) happy-path loading of int, str, float, bool, entity-ref, and wildcard params, (2) all five exception types (CanonConfigError, CanonResolutionError, CanonNoRuleError, CanonCycleError, ValidationError) triggered by their respective invalid inputs, and (3) round-trip serialization for YAML and JSON, then every test case passes and no test relies on mocking any of the five dependency features' public APIs


## Constraints
- Depends on: feature-001, feature-002, feature-003, feature-004, feature-005
- Complexity: high
