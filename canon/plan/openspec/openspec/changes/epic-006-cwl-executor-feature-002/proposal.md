# CWLRunResult Dataclass Definition

## Goal
CWLRunResult Dataclass Definition: Define the CWLRunResult dataclass for representing the result of a CWL workflow execution, including outputs, runner metadata, environment info, and exit status.

## Acceptance Criteria
- Given a successful CWL workflow run, when CWLRunResult is constructed with the cwltool stdout JSON, then the outputs field contains the parsed CWL output object with file locations and checksums
- Given a CWLRunResult object, when its runner_name field is accessed, then it returns the string cwltool matching the adapter that produced it
- Given a CWL workflow that exits with code 1, when CWLRunResult is constructed with exit_code=1, then accessing the exit_code attribute returns 1 and the stdout and stderr fields contain the captured output
- Given CWLRunResult is a dataclass, when two CWLRunResult instances are constructed with identical fields, then they compare as equal
- Given CWLRunResult is constructed with execution_environment dict containing type and image fields, when the field is accessed, then the dict is returned unchanged

## Constraints
- Complexity: low
