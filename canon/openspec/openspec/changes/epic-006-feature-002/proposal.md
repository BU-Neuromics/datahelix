# WorkflowRun provenance entity creation

## Goal
WorkflowRun provenance entity creation: After successful ingestion, create a WorkflowRun entity in Hippo that records the full provenance of the run: input_entity_ids (list of Hippo entity IDs that were inputs), output_entity_ids (list of ingested entity IDs), rule_name (from the CanonTask), executor_type, work_dir, started_at, finished_at, and status. WorkflowRun is a first-class Hippo entity type created via the standard entity creation endpoint.


## Acceptance Criteria
- After a successful run, a WorkflowRun entity exists in Hippo with all required provenance fields
- WorkflowRun.input_entity_ids lists all entity IDs that were REUSE or BUILD inputs to this task
- WorkflowRun.output_entity_ids lists all entity IDs ingested from canon_outputs.json
- WorkflowRun.rule_name matches the ProductionRule.name that was executed
- WorkflowRun.status is "SUCCEEDED" for successful runs and "FAILED" for failed runs
- WorkflowRun entity creation failure does not prevent output entity ingestion (best-effort provenance)

## Constraints
- Depends on: epic-006-feature-001
- Complexity: medium
