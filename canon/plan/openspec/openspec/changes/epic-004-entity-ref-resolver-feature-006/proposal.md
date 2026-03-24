# Workflow run operations in HippoQueryClient

## Goal
Workflow run operations in HippoQueryClient: Implement find_workflow_run method on HippoQueryClient for retrieving in-progress or failed WorkflowRun entities to prevent duplicate executions.

## Acceptance Criteria
- Given an existing WorkflowRun entity with status=running for a given rule and parameter set, when HippoQueryClient.find_workflow_run is called with those parameters and status=running, then it returns that WorkflowRun entity
- Given no WorkflowRun entity exists for the given parameters and status, when find_workflow_run is called, then it returns None without raising an exception
- Given multiple WorkflowRun entities exist for the same rule but different statuses, when find_workflow_run is called with status=failed, then only the failed run is returned
- Given a WorkflowRun query with valid entity_type and params, when the Hippo API returns an HTTP 4xx error, then find_workflow_run raises CanonResolutionError with the HTTP status code and response body in the message
- Given the Hippo instance is unreachable, when find_workflow_run is called, then it raises CanonResolutionError indicating connectivity failure

## Constraints
- Depends on: epic-004-entity-ref-resolver-feature-003
- Complexity: medium
