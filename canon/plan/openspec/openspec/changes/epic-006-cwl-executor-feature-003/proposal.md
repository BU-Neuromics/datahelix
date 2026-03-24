# CwltoolAdapter Implementation

## Goal
CwltoolAdapter Implementation: Implement CwltoolAdapter that invokes cwltool as a subprocess, constructs inputs.json, parses JSON output, and detects execution environment.

## Acceptance Criteria
- Given CwltoolAdapter is initialized with a valid work_dir and cwltool is installed on PATH, when run() is called with a valid CWL workflow path and an inputs dict containing string and File-type entries, then it writes an inputs.json file to work_dir whose contents match the provided inputs dict serialized as JSON
- Given CwltoolAdapter.run() is called with a valid CWL workflow path and inputs, when cwltool executes successfully (exit code 0) and emits JSON to stdout, then the returned CWLRunResult has exit_code equal to 0, outputs field containing the parsed JSON object from cwltool stdout, and runner_version containing a non-empty string matching the installed cwltool version
- Given CwltoolAdapter.run() is called, when the subprocess is invoked, then the command line includes 'cwltool' as the executable, followed by any configured cwltool_options, followed by the CWL workflow file path, followed by the inputs.json file path, in that exact order
- Given cwltool is not installed or not found on PATH, when CwltoolAdapter.validate_available() is called, then it raises CanonConfigError whose message includes the string 'cwltool' and contains installation instructions
- Given cwltool exits with a non-zero exit code and writes error details to stderr, when CwltoolAdapter.run() processes the result, then it raises CanonExecutorError whose message includes the numeric exit code and the captured stderr content verbatim
- Given cwltool_options is configured with ['--no-container', '--debug'], when CwltoolAdapter constructs the subprocess command, then '--no-container' and '--debug' appear in the argument list after 'cwltool' and before the CWL workflow file path
- Given CwltoolAdapter.run() is called and cwltool produces stdout that is not valid JSON, when the adapter attempts to parse the output, then it raises CanonExecutorError indicating that output parsing failed and includes the raw stdout content in the error context
- Given CwltoolAdapter.run() is called with a work_dir that does not yet exist, when the adapter prepares to write inputs.json, then it creates the work_dir directory (including intermediate parents) before writing the file

## Constraints
- Depends on: epic-006-cwl-executor-feature-001, epic-006-cwl-executor-feature-002
- Complexity: medium
