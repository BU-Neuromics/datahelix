# CWLExecutorAdapter ABC Definition

## Goal
CWLExecutorAdapter ABC Definition: Define the abstract base class CWLExecutorAdapter and CWLRunResult dataclass that standardize the interface for all CWL execution backends.

## Acceptance Criteria
- Given a class that subclasses CWLExecutorAdapter without implementing the run abstract method, when instantiated, then Python raises TypeError indicating the abstract method is not implemented
- Given a class that fully implements CWLExecutorAdapter including run and version methods, when instantiated and run is called with valid cwl_path and inputs, then no TypeError is raised
- Given CWLExecutorAdapter is imported from canon.executors.base, when inspected with inspect.isabstract, then it returns True confirming it cannot be instantiated directly
- Given CWLExecutorAdapter defines a requires_staging class attribute, when a subclass does not override it, then the default value of True is inherited
- Given CWLRunResult is defined as a dataclass, when instantiated with all required fields, then it can be constructed and its fields accessed without error

## Constraints
- Complexity: low
