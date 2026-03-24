# Sidecar Loader and Hippo Fields Expression Evaluator

## Goal
Sidecar Loader and Hippo Fields Expression Evaluator: Implement the sidecar loader that parses .canon.yaml sidecar files and evaluates hippo_fields expressions against CWL output JSON and CWL inputs to extract Hippo entity field values, with eager validation at load time for both output and input name references.


## Acceptance Criteria
- Given a valid star_align.canon.yaml sidecar file, when the sidecar loader parses it, then it returns a SidecarOutput object with entity_type, identity_fields, and hippo_fields attributes populated from the YAML
- Given a sidecar hippo_fields expression referencing outputs.bam.location, when evaluated against a CWL output JSON containing a bam File object, then the expression evaluates to the file URI string
- Given a sidecar hippo_fields expression referencing inputs.genome_build, when evaluated against the CWL inputs dict, then it returns the value that was passed as genome_build to the CWL workflow
- Given a sidecar output with an identity_field that is not present in hippo_fields, when the sidecar is validated at startup, then CanonRuleValidationError is raised with the missing field name
- Given a sidecar referencing a CWL output name that does not exist in the paired workflow's outputs block, when validated at startup, then CanonRuleValidationError is raised identifying the unknown output name
- Given a sidecar referencing a CWL input name that does not exist in the paired workflow's inputs block, when validated at startup, then CanonRuleValidationError is raised identifying the unknown input name
- Given a hippo_fields expression referencing an optional CWL output that resolved to None, when the expression is evaluated, then the corresponding field value is set to None without raising an error
- Given a hippo_fields expression referencing a required CWL output that resolved to null, when the expression is evaluated, then CanonIngestionError is raised identifying the required output name and the fact that it was unexpectedly null
- Given a .canon.yaml file with invalid YAML syntax, when the sidecar loader attempts to parse it, then CanonRuleValidationError is raised with a message describing the parse error and the file path
- Given a .canon.yaml file that is valid YAML but missing the required entity_type top-level key, when the sidecar loader parses it, then CanonRuleValidationError is raised identifying the missing required key
- Given a complete sidecar with entity_type, identity_fields, and hippo_fields referencing both CWL outputs and CWL inputs, when the loader parses the sidecar and evaluates all expressions against a full CWL output JSON and inputs dict, then it returns a fully populated result dict with every hippo_field resolved to its expected value and all identity_fields present in the result

## Constraints
- Depends on: epic-001-core-types-feature-001, epic-001-core-types-feature-002
- Complexity: medium
