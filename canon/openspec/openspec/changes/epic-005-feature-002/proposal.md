# ContainerAdapter (Docker and Singularity)

## Goal
ContainerAdapter (Docker and Singularity): Implement ContainerAdapter extending WorkflowExecutorAdapter. Supports Docker and Singularity runtimes via a ContainerRuntime enum (DOCKER, SINGULARITY). render() resolves the workflow identifier to a container image + script path. submit() runs docker run or singularity exec with the work directory mounted and inputs passed as environment variables. poll() inspects container status. collect_outputs() retrieves .canon_outputs.json from the mounted work directory.


## Acceptance Criteria
- ContainerAdapter accepts container_image and runtime (DOCKER or SINGULARITY) in CanonConfig executor settings
- Docker: submit() calls docker run --rm -e KEY=VALUE -v work_dir:/canon_work <image> <script>
- Singularity: submit() calls singularity exec --bind work_dir:/canon_work <image> <script>
- poll() returns correct RunStatus by inspecting docker/singularity container exit code
- collect_outputs() raises CanonExecutorError if .canon_outputs.json is absent after success
- ContainerRuntime.DOCKER and ContainerRuntime.SINGULARITY are the only valid runtime values

## Constraints
- Depends on: epic-004-feature-001
- Complexity: medium
