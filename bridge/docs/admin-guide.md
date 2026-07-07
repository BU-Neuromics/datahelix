# Administrator Guide

This guide covers platform administration tasks: managing users and API keys, reviewing
the audit log, and performing key rotation and maintenance procedures.

Requires `admin` role.

---

## Initial Setup

### 1. Initialize Bridge databases

```bash
bass-mgr bridge db init --config bridge.yaml
```

Creates the token store and API key tables. Safe to re-run.

### 2. Create the first admin key

On a fresh deployment, create the initial admin API key directly on the server (before
Bridge is accessible externally):

```bash
bass-mgr bridge api-keys create-admin --label "Initial admin key"
```

This prints a `datahelix_live_` key. Store it securely. Use it to bootstrap subsequent admin
operations.

### 3. Configure authentication mode

Edit `bridge.yaml` to set the auth mode:

```yaml
auth:
  mode: api_key          # Start with API keys; add OAuth2 later if needed
```

---

## User and Key Management

### List all API keys

```bash
datahelix auth list-keys --all          # Admin: shows all users' keys
```

### Revoke a specific key

```bash
datahelix auth revoke-key <key-id> --reason "Key exposed in repo"
```

Revocation is immediate. The key stops working on the next request.

### Revoke all keys for a user

```bash
datahelix admin users revoke-all-keys --user alice@uni.edu
```

Use this when a user leaves the organisation or a credential set is compromised.

### View key metadata

```bash
datahelix auth list-keys --all --user alice@uni.edu
```

Output includes: key ID, label, role, project scope, created date, last used date,
expiry (if set). Plaintext key is never shown after creation.

---

## Project Management

### Create a project

```bash
datahelix admin projects create \
  --name "lab-a" \
  --display-name "Genomics Lab A" \
  --description "CTE DLPFC cohort"
```

### Add a member

```bash
datahelix admin projects add-member \
  --project lab-a \
  --user alice@uni.edu \
  --role analyst
```

### Change a member's role

```bash
datahelix admin projects update-member \
  --project lab-a \
  --user alice@uni.edu \
  --role project_lead
```

### Remove a member

```bash
datahelix admin projects remove-member \
  --project lab-a \
  --user alice@uni.edu
```

### List project members

```bash
datahelix admin projects list-members --project lab-a
```

---

## Audit Log

### View recent auth events

```bash
# Last 50 auth events
datahelix admin audit auth --limit 50

# Filter by actor
datahelix admin audit auth --actor alice@uni.edu

# Filter by event type
datahelix admin audit auth --event key_revoked
```

### View recent request failures

```bash
# Non-200 requests in the last hour
datahelix admin audit requests --status 4xx,5xx --since 1h

# Unauthorized access attempts
datahelix admin audit requests --error insufficient_role,project_scope_denied
```

### Export audit log

```bash
# Export to JSON lines (for ingestion into SIEM or log aggregator)
datahelix admin audit export \
  --from 2026-08-01 \
  --to 2026-09-01 \
  --output audit-aug-2026.jsonl
```

### Audit log location

If the audit log backend is `file`, the default path is `/var/log/datahelix/audit.jsonl`.
Configure in `bridge.yaml`:

```yaml
observability:
  audit_log:
    enabled: true
    backend: file
    path: /var/log/datahelix/audit.jsonl
```

---

## Key Rotation Procedures

### Rotate an API key

Rotating a key issues a new key and revokes the old one. The old key stops working
immediately. Notify the key owner to update their environment variables or secrets manager.

```bash
# Admin rotating another user's key
datahelix auth rotate-key <key-id>

# Output:
# New key:  datahelix_live_...  (one-time display)
# Old key:  key_01jx...    (revoked)
```

### Rotate the JWT signing key

For RS256 deployments, rotate the signing key pair annually or after suspected compromise:

1. Generate a new key pair:
   ```bash
   openssl genrsa -out bridge_jwt_new.pem 4096
   openssl rsa -in bridge_jwt_new.pem -pubout -out bridge_jwt_new.pub.pem
   ```

2. Update `bridge.yaml` to reference the new key files.

3. Restart Bridge. Existing access tokens issued with the old key will fail verification
   immediately (they use the old public key). Active users will need to log in again.
   Refresh tokens are unaffected (they are opaque, not JWTs) and can be exchanged for
   new access tokens signed by the new key.

4. Revoke all refresh tokens if compromise is suspected:
   ```bash
   datahelix admin tokens revoke-all
   ```

---

## Sync Mismatch Review

Bridge logs sync mismatches when a Cappella pipeline run's outputs are not reflected in
Hippo. Review and resolve these regularly.

### List unresolved mismatches

```bash
datahelix admin sync mismatches --status unresolved
```

### View mismatch details

```bash
datahelix admin sync mismatches show <event-id>
```

Output includes: run ID, missing entities, actor, timestamp, recommended repair strategy.

### Resolve a mismatch

If the mismatch is expected (e.g., a run was deliberately cancelled):

```bash
datahelix admin sync mismatches resolve <event-id> --note "Run cancelled by user; no repair needed"
```

If the run should be resubmitted:

```bash
datahelix admin sync resubmit <run-id>
```

### Trigger a full consistency scan

```bash
datahelix admin sync scan
```

Runs a full cross-component consistency check. Results are stored in the sync event log
and available via `datahelix admin sync mismatches`.

---

## Monitoring

### Platform health

```bash
datahelix admin health
```

Or directly via HTTP:

```bash
curl https://datahelix.your-org.edu/api/v1/bridge/health
```

### Prometheus metrics

If `observability.metrics.enabled: true` in `bridge.yaml`, scrape:

```
https://datahelix.your-org.edu/api/v1/bridge/metrics
```

Key metrics to alert on:

| Metric | Alert condition |
|---|---|
| `bridge_auth_failures_total{type="revoked_token"}` | Spike → potential key compromise |
| `bridge_component_health` | Value = 0 → component down |
| `bridge_request_duration_seconds{quantile="0.99"}` | > 500ms → performance degradation |
| `bridge_sync_mismatches_total` | Sustained increase → pipeline integrity issue |

---

## Backup and Recovery

### What to back up

| Data | Location | Importance |
|---|---|---|
| Token store (SQLite) | `bridge.db` (configurable) | High — active sessions |
| API key store (SQLite) | Same DB or separate | Critical — long-lived credentials |
| Sync event log | Same DB | Medium — audit history |
| `bridge.yaml` | Config file | Critical — must be in version control |
| JWT signing keys | File paths in `bridge.yaml` | Critical — never lose private key |

### Token store loss

If the token store is lost:
- All active refresh tokens are invalidated — users must log in again.
- All API keys are invalidated — users must generate new keys.
- No DataHelix entity data is affected (that lives in Hippo).

Recovery: restore from backup, or have users create new keys via `datahelix auth create-key`.
