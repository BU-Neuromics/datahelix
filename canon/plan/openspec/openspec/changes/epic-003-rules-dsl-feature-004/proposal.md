# RulesLoader YAML Parsing

## Goal
RulesLoader YAML Parsing: Implement the RulesLoader to parse canon_rules.yaml files with parameter type dispatch.

## Acceptance Criteria
- Given a valid canon_rules.yaml file with properly formatted rules, when RulesLoader attempts to load the file, then all rules are parsed correctly without raising any exceptions or errors
- Given a canon_rules.yaml file with invalid YAML syntax, when RulesLoader attempts to load the file, then a YAML parsing exception is raised with an appropriate error message indicating the location and nature of the syntax error
- Given a canon_rules.yaml file containing multiple rule types (e.g., string, integer, boolean), when RulesLoader processes the file, then each rule type is correctly dispatched to its corresponding model based on the rule's parameter specifications
- Given a canon_rules.yaml file with missing required fields in rules, when RulesLoader attempts to parse the file, then a validation error is raised with a clear message identifying the missing field and the rule that caused the issue
- Given a canon_rules.yaml file with valid content but unsupported rule types, when RulesLoader attempts to load the file, then an appropriate exception is raised indicating that the rule type is not supported

## Constraints
- Complexity: medium
