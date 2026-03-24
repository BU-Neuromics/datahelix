# YAML Rules Parsing and Loading

## Goal
YAML Rules Parsing and Loading: Parse and load canon_rules.yaml file into memory with basic structure validation to ensure it contains required fields and proper syntax.

## Acceptance Criteria
- Given a valid canon_rules.yaml file with all required top-level keys (rule_sets, global_constraints), when the RulesLoader parses it, then it returns a dictionary containing each top-level key mapped to its parsed sub-structure
- Given a canon_rules.yaml file missing the required "rule_sets" key, when the RulesLoader validates the parsed structure, then it raises a ValidationException whose message includes the string "rule_sets" and identifies it as a missing required field
- Given a canon_rules.yaml file missing the required "global_constraints" key, when the RulesLoader validates the parsed structure, then it raises a ValidationException whose message includes the string "global_constraints" and identifies it as a missing required field
- Given a file containing invalid YAML syntax (e.g., unmatched braces or bad indentation), when the RulesLoader attempts to parse it, then it raises a ParseError whose message includes the line number where the syntax error occurs
- Given a canon_rules.yaml file where a required field is present but has a null value, when the RulesLoader validates the parsed structure, then it raises a ValidationException identifying the specific field and indicating it must not be null
- Given the file path points to a non-existent file, when the RulesLoader attempts to read it, then it raises a FileNotFoundError with a message containing the attempted file path
- Given a valid canon_rules.yaml file, when the RulesLoader successfully parses and validates it, then the returned dictionary preserves all scalar values, lists, and nested mappings exactly as defined in the source file without type coercion or data loss

## Constraints
- Complexity: low
