# CWL Workflow Path Resolution

## Goal
CWL Workflow Path Resolution: Resolve .canon.yaml sidecar file paths relative to each CWL workflow path and validate their existence.

## Acceptance Criteria
- Given a rule whose CWL workflow path is "workflows/align.cwl" rooted under "/repo", when the RulesLoader resolves the sidecar path, then it returns the absolute path "/repo/workflows/align.canon.yaml"
- Given a rule whose CWL workflow path is a relative path containing ".." segments (e.g., "../shared/trim.cwl"), when the RulesLoader resolves the sidecar path, then it normalizes the path and returns the correct absolute path to "shared/trim.canon.yaml" without ".." segments
- Given a rule whose CWL workflow path points to an existing CWL file and the corresponding .canon.yaml sidecar file exists on disk, when the RulesLoader validates the sidecar, then it returns successfully with no error
- Given a rule whose CWL workflow path points to an existing CWL file but no corresponding .canon.yaml sidecar file exists on disk, when the RulesLoader validates the sidecar, then it raises a SidecarMissingError whose message includes the expected sidecar file path
- Given a rule whose CWL workflow path points to a file that does not exist on disk, when the RulesLoader resolves paths, then it raises a WorkflowNotFoundError whose message includes the non-existent workflow path before attempting sidecar resolution
- Given multiple rules each with distinct CWL workflow paths, when the RulesLoader resolves sidecar paths for the batch, then each rule's sidecar path is resolved independently relative to its own workflow path, not relative to any shared base directory

## Constraints
- Complexity: medium
