# ContainerAdapter (Docker and Singularity)

## Goal
ContainerAdapter (Docker and Singularity): Implement ContainerAdapter extending WorkflowExecutorAdapter. Supports Docker and Singularity runtimes via a ContainerRuntime enum (DOCKER, SINGULARITY). render() resolves the workflow identifier to a container image + script path. submit() runs docker run or singularity exec with the work directory mounted and inputs passed as environment variables. poll() inspects container status. collect_outputs() retrieves .canon_outputs.json from the mounted work directory.

## Acceptance Criteria
- Given a CanonConfig executor settings object with container_image and DOCKER runtime, when ContainerAdapter is initialized, then it accepts the configuration and sets the runtime to ContainerRuntime.DOCKER
- Given a CanonConfig executor settings object with container_image and SINGULARITY runtime, when ContainerAdapter is initialized, then it accepts the configuration and sets the runtime to ContainerRuntime.SINGULARITY
- Given a ContainerAdapter with DOCKER runtime, when submit() is called, then it executes 'docker run --rm -e KEY=VALUE -v work_dir:/canon_work <image> <script>' command with proper environment variables and volume mapping
- Given a ContainerAdapter with SINGULARITY runtime, when submit() is called, then it executes 'singularity exec --bind work_dir:/canon_work <image> <script>' command with proper bind path and image execution
- Given a successful container execution, when poll() is called, then it returns RunStatus.SUCCEEDED by inspecting the container exit code
- Given a failed container execution, when poll() is called, then it returns RunStatus.FAILED by inspecting the container exit code
- Given a running container, when poll() is called, then it returns RunStatus.RUNNING by checking container status
- Given an executed workflow with missing .canon_outputs.json file, when collect_outputs() is called, then it raises CanonExecutorError
- Given invalid runtime value, when ContainerAdapter is initialized, then it raises ValueError for unsupported runtime types
- Given valid DOCKER and SINGULARITY enum values, when tested against ContainerRuntime, then only these two values are accepted as valid runtime options

## Constraints
- Depends on: epic-004-feature-001
- Complexity: medium
