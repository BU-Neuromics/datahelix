# Execution Plan and Task Models

## Goal
Execution Plan and Task Models: Implement models for execution plans, run handles, status tracking, and executor inputs.

## Acceptance Criteria
- Given an ExecutionTask model instance with inputs of each supported primitive type (string, int, float, boolean, null), when the instance is serialized to JSON and deserialized back, then every field round-trips to its original Python type without loss or coercion
- Given an ExecutionTask model with nested input structures (a dict containing a list of dicts), when serialized to JSON and deserialized, then the nested structure is identical to the original including key order, list length, and leaf-value types
- Given a RunHandle model schema that declares created_at as datetime, updated_at as datetime, status as a RunStatus enum, and execution_id as UUID, when a RunHandle is instantiated with correctly typed values, then validation passes and each field's Python type matches the schema declaration
- Given a RunHandle constructor is called with a non-UUID string for execution_id or a plain string for created_at, when validation runs, then a ValidationError is raised whose error detail names the offending field and expected type
- Given a RunHandle is instantiated with no optional arguments, when validation runs, then default values are applied (e.g., status defaults to PENDING, created_at defaults to current UTC time) and the resulting object passes full schema validation
- Given a RunStatus model tracking state transitions, when status is updated from PENDING to RUNNING and then from RUNNING to COMPLETED, then each transition is accepted and the model records the current status accurately after each update
- Given a RunStatus model in COMPLETED state, when an update attempts to transition status to RUNNING, then the model rejects the transition with an InvalidStateTransition error indicating the illegal source and target states
- Given an ExecutionTask with input fields subject to validation constraints (e.g., a required string field or an integer with a minimum value), when the task is constructed with inputs violating those constraints, then validation raises an error before serialization occurs identifying each violated constraint

## Constraints
- Depends on: feature-001
- Complexity: medium
