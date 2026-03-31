# Aperture CLI Reference (`bass`)

`bass` is the command-line interface for the BASS platform. It provides entity CRUD, ingestion,
schema inspection, provenance viewing, system status, and authentication management for the full
BASS platform stack (Hippo, Canon, Cappella, Bridge).

---

## Global Flags

These flags are accepted by every `bass` command:

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `table` | Output format: `table`, `json`, `csv` |
| `--no-color` | | off | Disable ANSI color codes |
| `--no-pager` | | off | Never page output (useful in scripts) |
| `--quiet` | `-q` | off | Suppress non-essential output; errors still go to stderr |
| `--config` | | `./aperture.yaml` | Path to aperture config file |
| `--hippo-url` | | (from config) | Override Hippo REST URL for this invocation |
| `--version` | | | Print `bass` version and exit |
| `--help` | `-h` | | Show help for the command |

**Environment variable overrides:**

| Variable | Equivalent flag |
|---|---|
| `BASS_FORMAT=json` | `--format json` |
| `BASS_NO_COLOR=1` | `--no-color` |
| `BASS_NO_PAGER=1` | `--no-pager` |
| `BASS_CONFIG=/path/to/aperture.yaml` | `--config` |
| `BASS_HIPPO_URL=http://...` | `--hippo-url` |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Partial failure (e.g., some ingest records failed validation) |
| `2` | Fatal error (connection failure, invalid config, unreadable file) |

---

## Entity Commands

### `bass list <entity_type>`

List entities of the given type. Returns paginated results sorted by creation time (newest
first by default).

```
bass list <entity_type> [flags]

Flags:
  --filter, -F key=value    Filter by field value. Repeatable. Multiple filters are ANDed.
  --limit, -n N             Max results (default: 50, max: 500)
  --offset N                Pagination offset (default: 0)
  --sort-by <field>         Sort field (default: created_at)
  --asc                     Sort ascending (default is descending)
  --include-unavailable     Include entities where is_available=false
  --columns col1,col2       Columns to display in table/csv output
```

**Examples:**

```bash
# List all Donors (first 50)
bass list Donor

# Filter by field
bass list Sample --filter tissue=DLPFC --filter is_available=true

# JSON output for scripting
bass list Sample --format json | jq '.[].external_id'

# Custom columns, sorted ascending
bass list SequencingDataset --sort-by created_at --asc \
  --columns external_id,sample_external_id,file_path

# Paginate: page 2
bass list Donor --limit 100 --offset 100
```

**Table output:** Column headers come from the schema. String fields are truncated to 40
characters with `…`. System fields (`id`, `is_available`) are always included unless
`--columns` overrides.

---

### `bass get <entity_type> <id>`

Fetch a single entity by its `external_id` or UUID.

```
bass get <entity_type> <id> [flags]

Flags:
  --format table|json|csv
```

**Examples:**

```bash
bass get Donor SUBJ-001
bass get Sample abc123-uuid --format json
```

**Table output:** Two-column key/value table. Reference fields are displayed as entity URIs
(`donor:SUBJ-001`). If the entity is not found, exits with code 2.

---

### `bass create <entity_type>`

Create a new entity. Accepts inline JSON (`--data`), a file (`--file`), or individual fields
(`--field key=value`). When run in a TTY with none of these flags, enters interactive mode.

```
bass create <entity_type> [flags]

Flags:
  --data '{"field": "value"}'   Inline JSON payload
  --file <path>                  JSON or YAML file with entity data
  --field key=value              Individual field (repeatable)
  --actor <identity>             Actor for provenance (default: $USER)
  --format table|json|csv        Output format for the created entity
  --dry-run                      Validate and print what would be created; do not write
```

**Examples:**

```bash
# Inline JSON
bass create Sample \
  --data '{"external_id":"S-042","tissue":"DLPFC","donor_id":"SUBJ-001"}' \
  --actor alice

# Individual fields
bass create Donor \
  --field external_id=SUBJ-010 \
  --field name="Alice W., 61F" \
  --field diagnosis=control \
  --actor alice

# From a YAML file
bass create Sample --file new_sample.yaml --actor alice

# Dry-run validation
bass create Sample --data '{"external_id":"S-001"}' --dry-run
```

**Interactive mode** (TTY, no `--data` / `--file` / `--field`):
Required fields are prompted first. Fields with `enum` constraints show valid values in
brackets. `Ctrl-C` cancels without writing. `--quiet` disables interactive mode.

**On validation error:** Prints error list to stderr. Exit code 1.

---

### `bass update <entity_type> <id>`

Update fields on an existing entity. Only supplied fields are modified (partial update).
System fields (`id`, `is_available`) cannot be updated via this command.

```
bass update <entity_type> <id> [flags]

Flags:
  --data '{"field": "value"}'   Fields to update (partial JSON)
  --file <path>                  JSON/YAML patch file
  --field key=value              Individual field update (repeatable)
  --actor <identity>             Actor for provenance (default: $USER)
  --format table|json|csv
  --dry-run
```

**Examples:**

```bash
bass update Sample S-042 --data '{"tissue":"frontal_cortex"}' --actor bob
bass update Donor SUBJ-001 --field diagnosis="control" --actor alice
```

---

### `bass set-availability <entity_type> <id> <true|false>`

Toggle entity availability. Creates a provenance event and updates `is_available`.

```
bass set-availability <entity_type> <id> <true|false> [flags]

Flags:
  --actor <identity>    Actor for provenance (default: $USER)
  --reason <text>       Reason string written to the provenance event
```

**Examples:**

```bash
# Mark unavailable (e.g., failed QC)
bass set-availability Sample S-042 false --actor alice --reason "sample failed QC"

# Restore availability
bass set-availability Sample S-042 true --actor alice
```

---

### `bass search <entity_type> <query>`

Full-text or fuzzy search across entities. Delegates to Hippo's FTS5 search.

```
bass search <entity_type> <query> [flags]

Flags:
  --field <field_name>    Restrict search to a specific field (default: all indexed fields)
  --limit N               Max results (default: 10, max: 100)
  --format table|json|csv
```

**Examples:**

```bash
bass search Donor "chronic traumatic encephalopathy"
bass search Sample "DLPFC" --field tissue --limit 20 --format json
```

**Table output** includes a relevance score column. If the entity type has no full-text
searchable fields, prints a warning to stderr and exits with code 0 (empty results).

---

## Provenance Commands

### `bass history <entity_type> <id>`

Show the provenance event log for an entity. Newest events first.

```
bass history <entity_type> <id> [flags]

Flags:
  --limit N               Max events (default: 20)
  --format table|json|csv
```

**Examples:**

```bash
bass history Donor SUBJ-001
bass history Sample S-042 --format json --limit 50
```

**Table columns:** `timestamp`, `event_type`, `actor`, `changes` (brief summary), `schema_version`.

**JSON output** includes full `previous_value` / `new_value` for each changed attribute.

---

## Schema Commands

### `bass schema list`

List all entity types defined in the loaded schema.

```
bass schema list [flags]

Flags:
  --format table|json|csv
```

**Table columns:** `entity_type`, `field_count`, `relationship_count`, `searchable`, `validator_count`.

---

### `bass schema show <entity_type>`

Show field and relationship definitions for a single entity type.

```
bass schema show <entity_type> [flags]

Flags:
  --format table|json|csv
```

**Example output:**

```
Entity type: Sample

Fields (6):
  Field            Type      Required  Indexed  Searchable
  ─────────────────────────────────────────────────────────
  external_id      string    yes       yes      —
  tissue           string    yes       yes      —
  diagnosis        string    no        yes      —
  donor_id         string    yes       yes      —
  is_available     bool      yes       yes      —
  created_at       datetime  yes       yes      —

Relationships (1):
  Field   Target type  Via field
  ──────────────────────────────
  donor   Donor        donor_id

Validators (1):
  tissue must be one of: DLPFC, frontal_cortex, temporal_lobe, cerebellum
```

---

## Ingestion Commands

### `bass ingest <entity_type> <file>`

Batch-ingest from a CSV or JSON Lines file via Hippo's `IngestionPipeline`.

```
bass ingest <entity_type> <file> [flags]

Flags:
  --actor <identity>              Actor for provenance (default: $USER)
  --dry-run                       Validate all records; do not write
  --on-conflict skip|update|error Conflict strategy (default: error)
  --format table|json             Summary output format
```

**Examples:**

```bash
# Standard ingest
bass ingest Sample samples.csv --actor alice

# Dry-run validation (no writes)
bass ingest Sample samples.csv --dry-run

# Upsert mode
bass ingest Sample samples.csv --on-conflict update --actor alice
```

**Progress bar** (large files):

```
[████████████░░░░] 800/1000 records  |  created: 750  updated: 48  errors: 2
```

**Summary output:**

```
Ingestion complete — 1000 records processed in 28.4s

  Result      Count
  ──────────────────
  Created     750
  Updated     48
  Unchanged   200
  Errors      2

2 errors written to: samples_errors.csv
```

Error rows go to `<input_file>_errors.csv` — not mixed into stdout.

**Exit codes:**
- `0` — all records ingested without error
- `1` — some records failed validation (partial success)
- `2` — ingestion aborted (connection failure, unreadable file)

---

## System Commands

### `bass status`

Check connectivity and deployment health for all configured backends.

```
bass status [flags]

Flags:
  --format table|json
```

**Example output:**

```
BASS Platform Status

  Component   Mode    URL / Path              Status    Version   Entities
  ────────────────────────────────────────────────────────────────────────
  Hippo       sdk     ./hippo.yaml            ✓ OK      0.4.2     12,341
  Cappella    —       (not configured)        — N/A
  Canon       —       (not configured)        — N/A
  Bridge      —       (not configured)        — N/A

Schema: omics_v2.yaml  (version: a3f7b2c1)  |  Entity types: 6
```

**Exit codes:** `0` — all configured backends healthy; `1` — at least one unreachable;
`2` — invalid/unreadable configuration.

---

## Config Commands

### `bass config show`

Print the fully resolved configuration with source annotations.

```bash
bass config show
```

```yaml
hippo:
  mode: sdk           # source: project config (./aperture.yaml)
  config: ./hippo.yaml  # source: project config
output:
  format: table       # source: default
  pager: auto         # source: default
  color: auto         # source: default
```

---

### `bass config get <key>`

Read a single resolved config value.

```bash
bass config get hippo.mode
# → sdk

bass config get hippo.url
# → http://localhost:8001
```

---

### `bass config set <key> <value>`

Write a key to the user config (`~/.bass/aperture.yaml`). Does not modify project config
(`./aperture.yaml`).

```bash
bass config set hippo.url http://hippo.internal:8000
bass config set output.format json
```

---

## Shell Completion

Install completions for your shell:

```bash
# Bash
bass --install-completion bash
# Add to ~/.bashrc: source ~/.bass-completion.bash

# Zsh
bass --install-completion zsh

# Fish
bass --install-completion fish
```

**Dynamic completions:** `<entity_type>` arguments complete from the loaded schema. `--filter`
keys complete from field names for the current entity type. Falls back to static completions
silently if Hippo is unavailable.

---

## Authentication Commands

These commands manage credentials for multi-user deployments that use Bridge for
authentication. They are not required for local single-user (SDK mode) deployments.

### `bass login`

Authenticate interactively with the BASS platform (Device Code flow). Opens a browser
for authentication with your institution's identity provider.

```
bass login [flags]

Flags:
  --bridge-url <url>    Bridge URL (default: from config or BASS_BRIDGE_URL)
  --force               Force re-authentication even if a valid session exists
```

**Example:**

```bash
bass login
# Opening browser for authentication...
# Waiting for authentication (expires in 900 seconds)...
# ✓ Authenticated as alice@uni.edu (role: analyst, projects: lab-a, lab-b)
# Session stored in ~/.bass/tokens.json
```

Tokens are stored in `~/.bass/tokens.json` (encrypted via OS keychain where available).
Subsequent `bass` commands use this session automatically.

---

### `bass logout`

Revoke the current session tokens and remove local credentials.

```
bass logout [flags]

Flags:
  --all    Also revoke all other active sessions for this account (server-side)
```

**Example:**

```bash
bass logout
# ✓ Session revoked. Tokens removed from ~/.bass/tokens.json
```

---

### `bass auth whoami`

Display the currently authenticated identity and permissions.

```bash
bass auth whoami
```

Output:

```
Actor:     alice@uni.edu
Role:      analyst
Projects:  lab-a, lab-b
Auth via:  session token (expires in 6d 23h)
Bridge:    https://bass.uni.edu
```

---

### `bass auth create-key`

Create a long-lived API key for non-interactive use (scripts, pipelines, CI/CD).

```
bass auth create-key [flags]

Flags:
  --label <text>          Human-readable key name (required)
  --role <role>           Role for this key: admin, project_lead, analyst, viewer, service
                          (default: same as current user; cannot exceed current user's role)
  --project <name>        Restrict key to a specific project (optional)
  --expires <date>        Expiry date in YYYY-MM-DD format (optional; no expiry by default)
```

**Example:**

```bash
bass auth create-key --label "Lab A notebook key" --role analyst --project lab-a

# Output:
# API key created successfully.
#
# Key:   bass_live_7f3a8b2c4d5e...  ← store this now, shown only once
# Label: Lab A notebook key
# Role:  analyst
# Scope: project: lab-a
# ID:    key_01jx...
```

The key is displayed **once**. Store it immediately in a password manager or secrets
manager. Use via `Authorization: Bearer <key>` header or `BASS_API_KEY` environment variable.

---

### `bass auth list-keys`

List API keys for the current user (or all keys for admins).

```
bass auth list-keys [flags]

Flags:
  --all           Show all users' keys (admin only)
  --user <actor>  Filter by user (admin only)
  --format table|json|csv
```

**Example:**

```bash
bass auth list-keys
```

Output:

```
ID           Label                   Role      Project  Created     Last used   Expires
───────────  ──────────────────────  ────────  ───────  ──────────  ──────────  ───────
key_01jx...  Lab A notebook key      analyst   lab-a    2026-10-15  2026-11-01  —
key_02ky...  Pipeline runner         service   lab-b    2026-09-01  2026-11-02  —
```

---

### `bass auth revoke-key`

Immediately revoke an API key. The key stops working on the next request.

```
bass auth revoke-key <key-id> [flags]

Flags:
  --reason <text>    Reason for revocation (logged to audit trail)
```

**Example:**

```bash
bass auth revoke-key key_01jx... --reason "key exposed in repo"
# ✓ Key key_01jx... revoked. It will no longer authenticate.
```

---

### `bass auth rotate-key`

Rotate an API key: creates a new key and revokes the old one atomically.

```
bass auth rotate-key <key-id>
```

The old key is immediately revoked. The new key is displayed once.

```bash
bass auth rotate-key key_01jx...
# New key: bass_live_9a1b2c3d...  ← update your environment variable/secrets manager
# Old key: key_01jx... (revoked)
```

---

## Configuration File Reference

`aperture.yaml` (project config) or `~/.config/bass/aperture.yaml` (user config):

```yaml
hippo:
  mode: sdk                  # "sdk" (local) or "rest" (remote, via Bridge)
  config: ./hippo.yaml       # path to hippo.yaml (sdk mode only)
  url: http://localhost:8001 # Hippo REST URL (rest mode)

bridge:
  url: https://bass.uni.edu  # Bridge base URL (multi-user deployments)
  # API key: set BASS_API_KEY environment variable (not stored in config)

output:
  format: table              # default output format: table | json | csv
  pager: auto                # pager: auto | always | never
  color: auto                # color: auto | always | never
```

**Authentication environment variables:**

| Variable | Description |
|---|---|
| `BASS_API_KEY` | API key for non-interactive auth. Set this in scripts and CI pipelines. |
| `BASS_BRIDGE_URL` | Bridge base URL. Overrides `bridge.url` in config. |
| `BASS_NO_KEYCHAIN` | Set to `1` to disable OS keychain integration for token storage. |

Config keys can be set via `bass config set`, environment variables, or CLI flags.
CLI flags take precedence over env vars, which take precedence over config files.
