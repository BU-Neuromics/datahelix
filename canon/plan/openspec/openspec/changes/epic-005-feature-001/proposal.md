# LocalProcessAdapter

## Goal
LocalProcessAdapter: Implement LocalProcessAdapter extending WorkflowExecutorAdapter. render() resolves the workflow identifier to a .sh script path relative to config.rules_dir (e.g., pipelines/star_align -> pipelines/star_align.sh) and constructs ExecutorInputs with the script path and input bindings. submit() runs the script as a subprocess with inputs passed as environment variables, setting CANON_WORK_DIR. poll() checks the subprocess returncode. collect_outputs() returns the path to $CANON_WORK_DIR/.canon_outputs.json.


## Acceptance Criteria
- Given a workflow identifier "pipelines/star_align", when LocalProcessAdapter.render() is called, then it should return ExecutorInputs with script_path set to "pipelines/star_align.sh" and input bindings as environment variables
- Given a subprocess has been started by submit(), when poll() is called immediately, then it should return RunStatus.RUNNING
- Given a subprocess has completed with exit code 0, when poll() is called, then it should return RunStatus.SUCCEEDED
- Given a subprocess has completed with non-zero exit code, when poll() is called, then it should return RunStatus.FAILED
- Given a subprocess has been started with input bindings, when collect_outputs() is called, then it should return the Path to .canon_outputs.json file under CANON_WORK_DIR
- Given a subprocess has been started, when collect_outputs() is called and .canon_outputs.json doesn't exist, then it should raise CanonExecutorError
- Given LocalProcessAdapter.submit() is called with ExecutorInputs, when the subprocess starts, then all input bindings from ExecutorInputs.inputs should be passed as environment variables to the subprocess
- Given LocalProcessAdapter.submit() is called, when the subprocess starts, then CANON_WORK_DIR environment variable should be set to a unique run directory under config.work_dir

## Constraints
- Depends on: epic-004-feature-001
- Complexity: medium
