# Integration tests for LocalProcessAdapter and CLI

## Goal
Integration tests for LocalProcessAdapter and CLI: Write integration tests that run a real LocalProcessAdapter against a trivial test workflow script (writes a valid .canon_outputs.json). Test the full canon run CLI path end-to-end with a mock Hippo server (httpretty or responses library). Test canon plan CLI with a mocked Hippo that returns no entities (all BUILD) and with one that returns an existing entity (REUSE).


## Acceptance Criteria
- Integration test runs LocalProcessAdapter with a real subprocess script and verifies RunStatus.SUCCEEDED
- Integration test verifies .canon_outputs.json is read and entities would be posted to Hippo
- canon plan CLI integration test with mocked Hippo shows correct REUSE/BUILD tree output
- canon run CLI integration test with mocked Hippo plus LocalProcessAdapter completes without error
- All integration tests are marked with pytest.mark.integration and can be skipped with -m not integration

## Constraints
- Depends on: epic-008-feature-001, epic-007-feature-002
- Complexity: medium
