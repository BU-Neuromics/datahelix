# WorkflowExecutorAdapter ABC

## Goal
WorkflowExecutorAdapter ABC: Define the WorkflowExecutorAdapter abstract base class with four abstract methods: render(task: CanonTask) -> ExecutorInputs, submit(inputs: ExecutorInputs) -> RunHandle, poll(handle: RunHandle) -> RunStatus, and collect_outputs(handle: RunHandle) -> Path. Include docstrings specifying the workflow identifier resolution convention for each adapter type. Define the executor adapter plugin entry point group canon.executor_adapters.


## Acceptance Criteria
- WorkflowExecutorAdapter is an ABC; instantiating it directly raises TypeError
- A subclass missing any of the 4 abstract methods raises TypeError on instantiation
- render(), submit(), poll(), collect_outputs() are declared as @abstractmethod
- WorkflowExecutorAdapter accepts CanonConfig in __init__ for access to work_dir and executor settings
- Entry point group canon.executor_adapters is documented in the module docstring

## Constraints
- Depends on: epic-001-feature-004
- Complexity: low
