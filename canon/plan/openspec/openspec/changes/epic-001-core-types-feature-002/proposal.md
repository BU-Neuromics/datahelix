# Exception hierarchy implementation

## Goal
Exception hierarchy implementation: Implement the full exception hierarchy including CanonConfigError, CanonResolutionError, CanonNoRuleError, and CanonCycleError.

## Acceptance Criteria
- Given a configuration file containing invalid YAML syntax (e.g., unmatched brackets or bad indentation), when CanonConfig.parse() is called with that file, then it raises CanonConfigError whose 'line' field is an int matching the 1-based line number of the syntax error and whose 'message' field contains a human-readable description of the problem
- Given a configuration where ruleA depends on ruleB and ruleB depends on ruleA, when the dependency resolution process executes, then it raises CanonCycleError whose 'cycle' field is a list containing exactly ['ruleA', 'ruleB', 'ruleA'] representing the full circular path
- Given a configuration where ruleA references ruleC and ruleC is not defined anywhere in the configuration, when the dependency resolution process executes, then it raises CanonNoRuleError whose 'rule' field equals the string 'ruleC' exactly as referenced in the configuration
- Given a syntactically valid configuration file where all referenced rules exist and all parameter values conform to their declared types, when CanonConfig.validate() is called, then it returns without raising any exception
- Given a configuration with valid YAML syntax but containing two invalid parameter values (e.g., ruleA.timeout set to a string instead of int, ruleB.mode set to an unrecognized enum value), when CanonConfig.validate() is called, then it raises CanonConfigError whose 'errors' field is a list of length 2 where each entry contains both 'field' (the dot-path to the invalid parameter) and 'message' (a specific description of the validation failure)
- Given any CanonCycleError or CanonNoRuleError instance, when checked with isinstance() against CanonResolutionError, then the check returns True, confirming both are subclasses of CanonResolutionError
- Given any CanonConfigError or CanonResolutionError instance, when checked with isinstance() against a common CanonError base class, then the check returns True, confirming the full hierarchy roots at a single base exception

## Constraints
- Complexity: low
