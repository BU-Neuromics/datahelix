# CanonSpec dataclass implementation

## Goal
CanonSpec dataclass implementation: Implement the CanonSpec dataclass that serves as the core representation of canonical specifications. CanonSpec holds typed fields (scalars and entity references) and supports validation, default values, enum constraints, pattern constraints, and YAML round-trip serialization.


## Acceptance Criteria
- Given a CanonSpec dataclass definition with typed fields (str, int, bool, float, Optional, List, Dict) and a valid input dict matching that schema, when CanonSpec is instantiated from the dict, then all fields are populated with correct Python types and no validation error is raised

- Given an input dict where a field value has an incompatible type (e.g. a string "abc" assigned to an int-typed field), when CanonSpec validation runs, then a TypeError is raised whose message includes the field name, the provided type, and the expected type

- Given an input dict missing a required field (a field with no default value), when CanonSpec validation runs, then a ValueError is raised whose message names the missing field and its expected type

- Given a CanonSpec dataclass with optional fields that declare default values, when instantiated with an input dict that omits those optional fields, then the instance contains the declared default values and passes validation

- Given a CanonSpec with an enum-typed field whose allowed values are ["DRAFT", "ACTIVE", "DEPRECATED"], when instantiated with an invalid enum value "UNKNOWN", then a ValueError is raised whose message lists the valid options for that field

- Given a CanonSpec instance containing nested objects and lists (e.g. a list of sub-spec dicts, a nested metadata dict), when serialized to a YAML string via yaml.dump and deserialized back via yaml.safe_load, then the round-tripped data is structurally equal to the original with identical Python types for every value

- Given a CanonSpec with a field constrained by a regex pattern (e.g. field "id" must match ^[a-z][a-z0-9-]*$), when instantiated with a value violating the pattern (e.g. "123-invalid"), then a ValueError is raised whose message includes the field name and the expected pattern

- Given a CanonSpec with a List[SubSpec] field where SubSpec has its own required fields, when one item in the list is missing a required SubSpec field, then validation raises a ValueError whose message includes the list field name, the item index, and the missing sub-field name

- Given a CanonSpec dataclass with nested self-referential structures that form a circular reference, when serialization is attempted, then the serializer detects the cycle and raises a clear error without entering infinite recursion

- Given a CanonSpec instance containing only scalar values (str, int, float, bool) and string values, when serialized to JSON via json.dumps and deserialized back via json.loads, then the round-tripped data is structurally equal to the original. When the instance also contains EntityRef fields, the serializer delegates to EntityRef's to_dict() method so the full instance is JSON-serializable without error.


## Constraints
- Depends on: epic-001-core-types-feature-002, epic-001-core-types-feature-003
- Complexity: medium
