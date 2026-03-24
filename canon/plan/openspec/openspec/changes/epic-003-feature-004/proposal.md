# Sidecar Consistency Validation

## Goal
Sidecar Consistency Validation: Validate consistency between rule specifications and their corresponding .canon.yaml sidecars including tool version matching and identity field references.

## Acceptance Criteria
- Given a rule specifying tool "samtools" at version "1.17" and its .canon.yaml sidecar declaring tool "samtools" at version "1.19", when the RulesLoader validates the rule-sidecar pair, then it raises a ToolVersionError whose message includes the tool name "samtools", the rule-declared version "1.17", and the sidecar-declared version "1.19"
- Given a rule specifying tool "bwa" at version "0.7.17" and its .canon.yaml sidecar declaring the same tool at the same version "0.7.17", when the RulesLoader validates the rule-sidecar pair, then no ToolVersionError is raised and validation succeeds for that tool entry
- Given a rule referencing identity_field "sample_id" but the corresponding .canon.yaml sidecar defines only identity_fields ["library_id", "run_id"], when the RulesLoader processes the rule, then it throws an InvalidIdentityFieldError whose message includes the unresolved field name "sample_id" and the list of valid identity fields from the sidecar
- Given a rule referencing identity_field "sample_id" and the .canon.yaml sidecar includes "sample_id" in its identity_fields list, when the RulesLoader processes the rule, then no InvalidIdentityFieldError is raised for that field reference
- Given rule A declaring a produces spec with output key "aligned_bam" and rule B's .canon.yaml sidecar also declaring a produces spec with output key "aligned_bam", when the RulesLoader checks cross-rule consistency, then it raises a DuplicateProducesSpecError whose message identifies both the conflicting output key "aligned_bam" and the sources (rule A and rule B's sidecar) that declare it
- Given a rule with a .canon.yaml sidecar that contains a tool entry not referenced anywhere in the rule's inputs, outputs, or params, when the RulesLoader validates the pair, then it raises an UnreferencedSidecarToolWarning or equivalent diagnostic identifying the extraneous tool entry
- Given a rule file that has no corresponding .canon.yaml sidecar file on disk, when the RulesLoader attempts to validate sidecar consistency for that rule, then it raises a MissingSidecarError whose message includes the expected sidecar file path
- Given a .canon.yaml sidecar with a malformed YAML structure (e.g., invalid syntax or missing required top-level keys), when the RulesLoader attempts to parse it, then it raises a SidecarParseError whose message includes the sidecar file path and the nature of the parse failure

## Constraints
- Complexity: high
