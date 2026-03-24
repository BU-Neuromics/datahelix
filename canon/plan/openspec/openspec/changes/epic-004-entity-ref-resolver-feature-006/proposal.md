# Workflow run operations in HippoQueryClient

## Goal
Workflow run operations in HippoQueryClient: Implement find_workflow_run method on HippoQueryClient for retrieving in-progress or failed WorkflowRun entities to prevent duplicate executions.

## Acceptance Criteria
- Given a WorkflowRun entity exists in Hippo with rule_id="rule-A", params={"sample":"S1"}, and status="running", when HippoQueryClient.find_workflow_run is called with rule_id="rule-A", params={"sample":"S1"}, and status="running", then it returns a WorkflowRun object whose id, rule_id, params, and status fields match the stored entity
- Given no WorkflowRun entity exists matching rule_id="rule-B", params={"sample":"S2"}, status="running", when find_workflow_run is called with those parameters, then it returns None and does not raise any exception
- Given three WorkflowRun entities exist for rule_id="rule-A" with statuses "completed", "failed", and "running" respectively, when find_workflow_run is called with rule_id="rule-A" and status="failed", then it returns only the WorkflowRun with status="failed" and does not return the completed or running entities
- Given the caller provides valid rule_id and params, when the Hippo API responds with an HTTP 4xx status code (e.g., 404 or 422), then find_workflow_run raises CanonResolutionError whose message includes both the numeric HTTP status code and the response body text
- Given the caller provides valid rule_id and params, when the Hippo API responds with an HTTP 5xx status code (e.g., 500 or 503), then find_workflow_run raises CanonResolutionError whose message indicates a server-side error and includes the HTTP status code
- Given the Hippo instance is unreachable (connection refused or DNS resolution failure), when find_workflow_run is called, then it raises CanonResolutionError whose message indicates a connectivity failure and includes the underlying connection error detail
- Given multiple WorkflowRun entities exist for the same rule_id and params but with different statuses, when find_workflow_run is called with status="running", then the returned WorkflowRun has status="running" and the method does not modify or delete any existing entities
- Given find_workflow_run is called with a status value that is not a recognized WorkflowRun status (e.g., status="invalid_status"), when the call is made, then it raises a ValueError or CanonResolutionError before issuing any network request

## Constraints
- Depends on: epic-004-entity-ref-resolver-feature-003
- Complexity: medium
