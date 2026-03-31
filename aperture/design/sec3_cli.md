## 3. CLI Design

**Depends on:** sec1 (scope, personas, command taxonomy), sec2 (architecture, backend protocol, command tree outline)
**Feeds into:** sec6 (NFR — startup time, responsiveness targets), Implementation

---

### 3.1 Design Goals

The `bass` CLI is the primary user surface for the BASS platform in v0.1. The design is guided
by four principles:

1. **Approachability** — A bioinformatician with no prior BASS experience can run `bass list Sample`
   and get results without reading documentation.
2. **Scriptability** — All commands produce machine-readable output (`--format json`). Exit codes
   are stable and documented. No interactive prompts on stdout.
3. **Discoverability** — `--help` at every level shows concise examples. Unknown inputs produce
   actionable error messages, not stack traces.
4. **Consistency** — All commands follow the same flag conventions, output structure, and error
   behavior. Learning one command transfers to all others.

---

### 3.2 Command Taxonomy

The `bass` command tree for v0.1 organises all operations into seven top-level groups:

```
bass <command> [subcommand] [args...] [flags...]
```

| Command | Group | Summary |
|---|---|---|
| `bass list` | Entity | List entities of a given type |
| `bass get` | Entity | Fetch a single entity by ID |
| `bass create` | Entity | Create a new entity |
| `bass update` | Entity | Update fields on an existing entity |
| `bass set-availability` | Entity | Mark an entity available or unavailable |
| `bass search` | Entity | Full-text / fuzzy search across entities |
| `bass history` | Provenance | Show provenance events for an entity |
| `bass schema list` | Schema | List all registered entity types |
| `bass schema show` | Schema | Show field definitions for an entity type |
| `bass ingest` | Ingestion | Trigger a batch ingestion from a flat file |
| `bass status` | System | Show connectivity and deployment health |
| `bass config get` | Config | Read a config key |
| `bass config set` | Config | Write a config key |
| `bass config show` | Config | Print the fully resolved configuration |

Commands deferred to v0.2: `bass resolve`, `bass reconcile`, `bass login`, `bass logout`.

---

### 3.3 Global Flags

These flags are accepted by every `bass` command:

| Flag | Short | Default | Description |
|---|---|---|---|
| `--format` | `-f` | `table` | Output format: `table`, `json`, `csv` |
| `--no-color` | | off | Disable ANSI color codes |
| `--no-pager` | | off | Never page output (useful in scripts) |
| `--quiet` | `-q` | off | Suppress all non-essential output; errors still printed to stderr |
| `--config` | | `./aperture.yaml` | Path to aperture config file |
| `--hippo-url` | | (from config) | Override Hippo REST URL for this invocation |
| `--version` | | | Print `bass` version and exit |
| `--help` | `-h` | | Show help for the command |

Format and color flags may also be set via environment variables:
- `BASS_FORMAT=json`
- `BASS_NO_COLOR=1`
- `BASS_NO_PAGER=1`

---

### 3.4 Entity Commands

#### 3.4.1 `bass list <entity_type>`

Lists entities of the specified type. Returns paginated results sorted by creation time
(descending by default).

```
bass list <entity_type> [flags]

Flags:
  --filter, -F key=value    Filter by field value. Repeatable. Multiple filters are ANDed.
  --limit, -n N             Max results to return (default: 50, max: 500)
  --offset N                Pagination offset (default: 0)
  --sort-by <field>         Sort field (default: created_at)
  --desc                    Sort descending (default: true)
  --asc                     Sort ascending
  --include-unavailable     Include entities where is_available=false
  --columns col1,col2       Comma-separated list of columns to display (table/csv only)
  --format table|json|csv   Output format (default: table)
```

**Examples:**

```bash
# List all Samples (first 50, table view)
bass list Sample

# List Samples from a specific tissue, JSON output
bass list Sample --filter tissue_type=DLPFC --format json

# List Samples with a specific donor, unavailable included, CSV
bass list Sample --filter donor_id=D001 --include-unavailable --format csv

# Custom columns
bass list Sample --columns id,name,tissue_type,created_at --limit 20

# Paginated iteration
bass list Sample --limit 100 --offset 0   # page 1
bass list Sample --limit 100 --offset 100 # page 2
```

**Table output (default):**
Column headers are derived from entity type schema. System fields (`id`, `is_available`) are
always included unless `--columns` overrides. String fields are truncated to 40 characters
with `…` suffix if needed.

**JSON output:**
Returns a JSON array of entity objects. Each object includes all stored fields plus system
fields (`id`, `is_available`, `entity_type`).

**CSV output:**
Header row matches the column selection. All values are quoted. Suitable for import into
spreadsheet tools or pipeline input.

---

#### 3.4.2 `bass get <entity_type> <id>`

Fetches a single entity by its UUID.

```
bass get <entity_type> <id> [flags]

Flags:
  --format table|json|csv
```

**Examples:**

```bash
bass get Sample abc123-...
bass get Sample abc123-... --format json
```

**Table output:** Renders as a two-column key/value table (field name | value). Relationship
references are displayed as URIs (e.g. `donor:D001`). Rich syntax highlighting for JSON-valued
fields.

If the entity does not exist, prints to stderr:
```
Error: Sample 'abc123' not found.
```
Exit code 1.

---

#### 3.4.3 `bass create <entity_type>`

Creates a new entity. Data can be provided inline (JSON string), from a file, or interactively
(if stdin is a TTY and neither `--data` nor `--file` is supplied).

```
bass create <entity_type> [flags]

Flags:
  --data '{"field": "value"}'   Inline JSON payload
  --file <path>                  JSON or YAML file with entity data
  --actor <identity>             Actor for provenance (default: $USER)
  --format table|json|csv        Output format for the created entity (default: table)
  --dry-run                      Validate and print what would be created; do not write
```

**Examples:**

```bash
# From inline JSON
bass create Sample --data '{"name": "S-001", "tissue_type": "DLPFC", "donor_id": "D001"}' --actor alice

# From file
bass create Sample --file new_sample.json --actor alice

# Dry-run validation
bass create Sample --data '{"name": "S-001"}' --dry-run
```

**Interactive mode** (when stdin is a TTY and no `--data`/`--file` provided):

```
Creating Sample. Enter values for each required field. Press Enter to accept defaults.
Leave optional fields blank to skip.

  name (string, required): █
  tissue_type (string, required): █
  donor_id (string, optional): █

Submit? [y/N]:
```

Interactive mode is disabled (exits with error) when `--quiet` is set or stdin is not a TTY,
so scripts never hang waiting for input.

**On success:** Prints the created entity (using `--format`). Exits with code 0.
**On validation failure:** Prints validation errors as a bulleted list to stderr. Exit code 1.

---

#### 3.4.4 `bass update <entity_type> <id>`

Updates fields on an existing entity. Only the supplied fields are modified (partial update).

```
bass update <entity_type> <id> [flags]

Flags:
  --data '{"field": "value"}'   Fields to update (partial JSON)
  --file <path>                  JSON/YAML patch file
  --actor <identity>             Actor for provenance (default: $USER)
  --format table|json|csv
  --dry-run
```

**Examples:**

```bash
bass update Sample abc123 --data '{"tissue_type": "frontal_cortex"}' --actor bob
bass update Sample abc123 --file patch.json --actor bob
```

**Behaviour notes:**
- Fields not in `--data` / `--file` are unchanged.
- Relationship fields (`ref` type) accept a target entity URI or UUID.
- System fields (`id`, `is_available`) cannot be updated via this command.
- On success, prints the updated entity.

---

#### 3.4.5 `bass set-availability <entity_type> <id> <true|false>`

Toggles entity availability. Uses Hippo's supersession model — this creates a provenance
event and updates `is_available`.

```
bass set-availability <entity_type> <id> <true|false> [flags]

Flags:
  --actor <identity>    Actor for provenance (default: $USER)
  --reason <text>       Optional reason string (written to provenance event)
```

**Examples:**

```bash
bass set-availability Sample abc123 false --actor alice --reason "sample failed QC"
bass set-availability Sample abc123 true  --actor alice
```

**Output:** Confirmation message on stdout. On failure, error to stderr with exit code 1.

---

#### 3.4.6 `bass search <entity_type> <query>`

Runs a full-text or fuzzy search across entities of the specified type. Delegates to Hippo's
FTS5 search capability.

```
bass search <entity_type> <query> [flags]

Flags:
  --field <field_name>    Restrict search to a specific field (default: all indexed fields)
  --limit N               Max results (default: 10, max: 100)
  --format table|json|csv
```

**Examples:**

```bash
bass search Sample "frontal lobe" --limit 20
bass search Sample "D001" --field donor_id
bass search Sample "DLPFC" --format json
```

**Output:** Table/JSON/CSV of matching entities with a relevance score column (table view only).
If the entity type has no searchable fields (`search: fts`), prints an informational warning to
stderr and exits with code 0 (empty results).

---

### 3.5 Provenance Command

#### 3.5.1 `bass history <entity_type> <id>`

Shows the provenance event log for an entity.

```
bass history <entity_type> <id> [flags]

Flags:
  --limit N               Max events to show (default: 20)
  --format table|json|csv
```

**Examples:**

```bash
bass history Sample abc123
bass history Sample abc123 --format json --limit 50
```

**Table output columns:** `event_type`, `actor`, `timestamp`, `changes` (brief summary of
what changed), `schema_version`.

Events are shown newest-first (default). The `--format json` output includes the full
`previous_value` / `new_value` fields for each changed attribute.

---

### 3.6 Schema Commands

#### 3.6.1 `bass schema list`

Lists all entity types defined in the loaded schema.

```
bass schema list [flags]

Flags:
  --format table|json|csv
```

**Table output columns:** `entity_type`, `field_count`, `relationship_count`, `searchable`
(yes/no), `validator_count`.

#### 3.6.2 `bass schema show <entity_type>`

Shows detailed field and relationship definitions for a single entity type.

```
bass schema show <entity_type> [flags]

Flags:
  --format table|json|csv
```

**Table output:**

```
Entity type: Sample
Fields (6):
  Field            Type      Required  Indexed  Searchable  Notes
  ─────────────────────────────────────────────────────────────
  name             string    yes       yes      fts         Human-readable identifier
  tissue_type      string    yes       yes      —
  donor_id         string    no        yes      —
  collection_date  date      no        no       —
  notes            text      no        no       fts
  batch_id         string    no        yes      —

Relationships (1):
  Field    Target type  Cardinality  Notes
  ──────────────────────────────────────────
  donor    Donor        many-to-one  Foreign key via donor_id

Validators (1):
  tissue_type must be one of: DLPFC, frontal_cortex, temporal_lobe, cerebellum
```

---

### 3.7 Ingestion Command

#### 3.7.1 `bass ingest <entity_type> <file>`

Triggers a batch ingestion from a flat file (CSV or JSON Lines). Delegates to Hippo's
`IngestionPipeline`.

```
bass ingest <entity_type> <file> [flags]

Flags:
  --actor <identity>     Actor for provenance records (default: $USER)
  --dry-run              Validate all records; do not write
  --on-conflict skip|update|error   Conflict resolution strategy (default: error)
  --format table|json    Summary output format (default: table)
```

**Examples:**

```bash
# Ingest from CSV
bass ingest Sample samples.csv --actor alice

# Dry-run to check for validation errors
bass ingest Sample samples.csv --dry-run

# Upsert mode: update existing entities if ID matches
bass ingest Sample samples.csv --on-conflict update --actor alice
```

**Progress reporting:** For large files, a Rich progress bar shows
`[████████████░░░░] 800/1000 records  |  created: 750  updated: 48  errors: 2`.

**Summary output (table):**

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

Error rows are written to a sidecar CSV (`<input_file>_errors.csv`) alongside the original
file, not to stdout. This allows the caller to inspect and resubmit failed rows without
parsing mixed output.

**Exit codes:**
- `0` — all records ingested without errors
- `1` — some records failed validation (partial success; see error CSV)
- `2` — ingestion aborted (connection failure, unreadable file, etc.)

---

### 3.8 System Status Command

#### 3.8.1 `bass status`

Checks connectivity to configured backends and prints deployment health.

```
bass status [flags]

Flags:
  --format table|json
```

**Output (table):**

```
BASS Platform Status

  Component     Mode   URL / Path               Status    Version   Entities
  ──────────────────────────────────────────────────────────────────────────
  Hippo         sdk    ./hippo.yaml             ✓ OK      0.4.1     12,341
  Cappella      —      (not configured)         — N/A
  Canon         —      (not configured)         — N/A
  Bridge        —      (not configured)         — N/A

Schema: omics_v2.yaml  (version: a3f7b2c1)  |  Entity types: 6
```

**Exit codes:**
- `0` — all configured backends healthy
- `1` — at least one configured backend is unreachable
- `2` — configuration is invalid or unreadable

---

### 3.9 Config Commands

#### 3.9.1 `bass config show`

Prints the fully resolved configuration, showing the source for each key (default, user config,
project config, env var, or CLI flag).

```bash
bass config show
```

**Output:**

```yaml
hippo:
  mode: sdk           # source: project config (./aperture.yaml)
  config: ./hippo.yaml  # source: project config

output:
  format: table       # source: default
  pager: auto         # source: default
  color: auto         # source: default
```

#### 3.9.2 `bass config get <key>`

Reads a single resolved config value.

```bash
bass config get hippo.mode
# → sdk
```

#### 3.9.3 `bass config set <key> <value>`

Writes a key to the user config file (`~/.bass/aperture.yaml`). Project config (`./aperture.yaml`)
is not modified by `bass config set`.

```bash
bass config set hippo.url http://hippo.internal:8000
bass config set output.format json
```

---

### 3.10 Shell Completion

Typer generates shell completions automatically. Installation:

```bash
# Bash
bass --install-completion bash
# output: source ~/.bass-completion.bash

# Zsh
bass --install-completion zsh

# Fish
bass --install-completion fish
```

**Dynamic completions:**

| Context | Completable values |
|---|---|
| `<entity_type>` argument | All entity types from loaded schema |
| `--filter key=...` | Field names for the current entity type |
| `bass config get/set <key>` | Known config keys |
| `--format` flag | `table`, `json`, `csv` |

Dynamic completions require a working Hippo connection. If the backend is unavailable during
tab-completion, static fallback completions are returned with no error output (completion
silently falls back to no-op rather than printing an error to the terminal).

---

### 3.11 Interactive Flows

#### 3.11.1 Create Interactive Mode

When `bass create` is run in a TTY with no `--data`/`--file`, it enters a guided interactive
field-entry flow:

```
Creating Sample

Required fields:
  name (string): █

  tissue_type (string) [DLPFC, frontal_cortex, temporal_lobe, cerebellum]: █

Optional fields (press Enter to skip):
  donor_id (string): █
  collection_date (YYYY-MM-DD): █
  notes (text): █

Preview:
  {
    "name": "S-042",
    "tissue_type": "DLPFC",
    "donor_id": "D001"
  }

Submit? [y/N]: █
```

Rules for interactive mode:
- Required fields are prompted before optional fields.
- Fields with `enum` constraints show valid values in brackets.
- `Ctrl-C` at any prompt cancels without creating an entity.
- `--dry-run` in interactive mode shows the preview but never submits.

#### 3.11.2 Conflict Confirmation

When `bass ingest` runs with `--on-conflict error` (default) and conflicts are detected, it
prints a summary and prompts for confirmation before aborting or proceeding:

```
Warning: 3 conflict(s) detected.

  ID        Current value   Incoming value
  ────────────────────────────────────────
  abc123    tissue=DLPFC    tissue=frontal_cortex
  def456    name=S-001      name=S-001a
  ghi789    ...             ...

Proceed? [y/N/skip]: █
```

In non-TTY mode (piped stdin), this prompt is skipped and the command exits with code 1
so the caller can handle conflicts programmatically.

---

### 3.12 Error Messages

Errors always go to stderr. The design standard:

| Situation | Message format |
|---|---|
| Entity not found | `Error: Sample 'abc123' not found.` |
| Validation failure (single) | `Error: Validation failed for 'tissue_type': 'XYZ' is not a valid value. Expected one of: DLPFC, frontal_cortex, ...` |
| Validation failure (multiple) | Bulleted list; each bullet is one violation |
| Connection failure | `Error: Cannot connect to Hippo at http://localhost:8000. Check 'bass config show' and ensure the server is running.` |
| Unknown entity type | `Error: Unknown entity type 'Sampel'. Did you mean 'Sample'? Run 'bass schema list' to see all types.` |
| Missing required flag | Typer's built-in message, e.g. `Missing argument 'ENTITY_TYPE'.` |
| Config file not found | `Warning: No aperture.yaml found. Using defaults. Run 'bass config show' to inspect current settings.` (stderr, not an error — continues with defaults) |

Fuzzy-match suggestions (e.g., "Did you mean 'Sample'?") are applied to entity type names.
The suggestion threshold is Levenshtein distance ≤ 2.

---

### 3.13 Exit Code Reference

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | User / data error: entity not found, validation failure, partial ingest failure |
| `2` | System error: connection failure, backend error, unreadable config |
| `3` | Auth error (v0.2) |

Exit codes are stable across minor versions. Scripts may rely on them.

---

### 3.14 Open Questions

| Question | Priority | Status |
|---|---|---|
| Should `bass list` support server-side cursor pagination in addition to offset? | Medium | Open — depends on Hippo REST API design (sec4 §4.x) |
| Should interactive mode support `$EDITOR` for multiline `text` fields? | Low | Deferred to post-v0.1 |
| Should `bass search` support cross-type search (all entity types)? | Low | Open |
| Fuzzy match threshold for "did you mean" suggestions: LD ≤ 2 or ≤ 3? | Low | Open |

---
