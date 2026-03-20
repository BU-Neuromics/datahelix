# LocalProcessAdapter

## Goal
LocalProcessAdapter: Implement LocalProcessAdapter extending WorkflowExecutorAdapter. render() resolves the workflow identifier to a .sh script path relative to config.rules_dir (e.g., pipelines/star_align -> pipelines/star_align.sh) and constructs ExecutorInputs with the script path and input bindings. submit() runs the script as a subprocess with inputs passed as environment variables, setting CANON_WORK_DIR. poll() checks the subprocess returncode. collect_outputs() returns the path to $CANON_WORK_DIR/.canon_outputs.json.


## Acceptance Criteria
- LocalProcessAdapter.render() maps "pipelines/star_align" to "pipelines/star_align.sh"
- submit() starts the subprocess and returns a RunHandle with the process PID in run_id
- poll() returns RunStatus.RUNNING if the process is alive, SUCCEEDED if returncode==0, FAILED otherwise
- collect_outputs() returns Path to .canon_outputs.json and raises CanonExecutorError if file does not exist
- All input bindings from ExecutorInputs.inputs are passed as environment variables to the subprocess
- CANON_WORK_DIR env var is set to a unique run directory under config.work_dir

## Constraints
- Depends on: epic-004-feature-001
- Complexity: medium
