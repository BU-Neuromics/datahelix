# Workflows and Triggers

Cappella automates ingest and resolution operations through a lightweight trigger system. Triggers fire actions — either on a schedule, on-demand, or in response to events emitted by other actions.

## Trigger Types

### Schedule Triggers

Run on a cron schedule:

```yaml
triggers:
  - name: nightly_donor_sync
    type: schedule
    schedule: "0 2 * * *"    # 2 AM every night
    action:
      type: ingest
      adapter: starlims_donors
    on_success: donors_synced
```

### Manual Triggers

Fire on demand via the CLI or API:

```bash
cappella trigger run nightly_donor_sync --config cappella.yaml
```

```bash
curl -X POST http://localhost:8000/triggers/nightly_donor_sync/run
```

### Internal Event Triggers

React to events emitted by other triggers. Use `on_success` on one trigger to chain into another:

```yaml
triggers:
  - name: nightly_donor_sync
    type: schedule
    schedule: "0 2 * * *"
    action:
      type: ingest
      adapter: starlims_donors
    on_success: donors_synced          # emits this event on success

  - name: resolve_after_sync
    type: internal_event
    event: donors_synced               # fires when donors_synced is emitted
    action:
      type: resolve
      entity_type: AlignmentFile
      parameters:
        genome: GRCh38
```

Cycles in trigger chains are detected at startup and rejected.

## Action Types

| Action | What it does |
|--------|-------------|
| `ingest` | Run an adapter's fetch → transform → upsert pipeline |
| `resolve` | Run collection resolution for an entity type and criteria |

```yaml
# Ingest action
action:
  type: ingest
  adapter: my_csv_adapter     # must match an adapter name in cappella.yaml

# Resolve action
action:
  type: resolve
  entity_type: GeneCounts
  parameters:
    genome: GRCh38
    annotation: ensembl110
```

## Trigger Status

List all configured triggers and their last-run status:

```bash
cappella status --config cappella.yaml
```

```json
{
  "triggers": {
    "nightly_donor_sync": {
      "status": "scheduled",
      "last_run": "2026-03-26T02:00:47Z",
      "last_result": "success"
    }
  }
}
```

## A Note on Workflow Execution

Cappella does not run bioinformatics analyses or CWL workflows directly. That is [Canon](../../canon/README.md)'s responsibility. When a `resolve` action needs a file to be produced, Cappella calls `canon.resolve()` and Canon handles REUSE/FETCH/BUILD internally.

For aggregate analyses (merging count matrices, running DESeq2 across a cohort) — these are downstream concerns for Composer or custom scripts that consume Cappella's `HarmonizedCollection` output.
