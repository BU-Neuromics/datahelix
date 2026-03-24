# Canon Status Command Implementation

## Goal
Canon Status Command Implementation: Implement the canon status CLI command that queries recent WorkflowRun entities from Hippo and displays their status, timing, and output information.

## Acceptance Criteria
- Given three or more WorkflowRun entities exist in Hippo with varying statuses (completed, failed, running), when the user runs `canon status`, then it prints a table to stdout containing columns rule_name, status, started_at, and output_entity_id with one row per WorkflowRun sorted by started_at descending, and exits with code 0
- Given zero WorkflowRun entities exist in Hippo, when the user runs `canon status`, then it prints the message "No recent workflow runs found" to stdout and exits with code 0
- Given WorkflowRun entities exist with status=failed and status=completed, when the user runs `canon status --failed`, then only rows where status=failed are displayed, each row includes the error_message field in addition to the standard columns, and the command exits with code 0
- Given a WorkflowRun entity exists with status=running and started_at set to 10 minutes ago, when the user runs `canon status`, then that row displays the started_at timestamp and an elapsed column showing a human-readable duration (e.g. "10m 3s") computed as the difference between now and started_at
- Given Hippo's API endpoint is unreachable (connection refused or timeout after 10 seconds), when the user runs `canon status`, then it prints an error message containing "unable to connect to Hippo" to stderr and exits with a non-zero exit code (exit code 1)
- Given more than 50 WorkflowRun entities exist in Hippo, when the user runs `canon status` without additional flags, then only the 25 most recent runs (by started_at) are displayed and a summary line "Showing 25 of N total runs" is printed below the table
- Given WorkflowRun entities exist, when the user runs `canon status --json`, then the output is a valid JSON array where each element contains the fields rule_name, status, started_at, output_entity_id, and (if status=running) elapsed_seconds, and the command exits with code 0

## Constraints
- Complexity: medium
