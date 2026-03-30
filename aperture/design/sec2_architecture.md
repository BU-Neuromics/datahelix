## 2. Architecture

**Depends on:** sec1 (scope, personas, design principles), Hippo sec2 (SDK & REST API), Hippo sec4 (API layer), Bridge INDEX (auth model — pending)
**Feeds into:** sec3 (CLI Design), sec4 (Web Interface), sec5 (API Client Libraries)

---

### 2.1 Component Overview

Aperture is structured as three layers that ship independently. Only the CLI layer is required
for v0.1. The web portal and client libraries are additive — they share the same backend
integration layer.

```
┌──────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                            │
│                                                                  │
│  ┌──────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │  CLI              │  │  Web Portal     │  │  Client Libs   │  │
│  │  `bass` command   │  │  (v0.2)         │  │  Python/R      │  │
│  │  Typer framework  │  │                 │  │  (v0.2)        │  │
│  └────────┬─────────┘  └────────┬────────┘  └───────┬────────┘  │
└───────────│──────────────────── │ ────────────────── │ ──────────┘
            │                     │                     │
┌───────────▼─────────────────────▼─────────────────────▼──────────┐
│                     Backend Integration Layer                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ HippoBackend │  │ CappellaBack │  │ BridgeAuth           │   │
│  │ (SDK or REST)│  │ (REST, v0.2) │  │ (token mgmt, v0.2)   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ OutputFormatter (table / JSON / CSV)                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
            │                     │
┌───────────▼─────────────────────▼────────────────────────────────┐
│                     BASS Component APIs                           │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐  ┌───────────┐ │
│  │ Hippo SDK   │  │ Hippo REST   │  │Cappella │  │  Bridge   │ │
│  │ (local)     │  │ (remote)     │  │ REST    │  │  Gateway  │ │
│  └─────────────┘  └──────────────┘  └─────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Package Structure

```
aperture/
│
├── cli/                            # CLI presentation layer
│   ├── main.py                     # Typer app, top-level command group
│   ├── commands/
│   │   ├── entity.py               # bass list, bass get, bass create, bass update
│   │   ├── search.py               # bass search
│   │   ├── schema.py               # bass schema list, bass schema show
│   │   ├── provenance.py           # bass history
│   │   ├── ingest.py               # bass ingest
│   │   ├── status.py               # bass status
│   │   └── config.py               # bass config get/set
│   └── display/
│       ├── formatters.py           # Table, JSON, CSV output renderers
│       └── pager.py                # Pagination for long output
│
├── backends/                       # Backend integration layer
│   ├── base.py                     # BackendProtocol — common interface
│   ├── hippo_sdk.py                # Local mode: wraps HippoClient directly
│   ├── hippo_rest.py               # Remote mode: wraps Hippo REST API via httpx
│   └── auth.py                     # Auth token management (Bridge, v0.2)
│
├── config/
│   ├── settings.py                 # Pydantic settings model (aperture.yaml / env vars)
│   └── defaults.py                 # Default configuration values
│
├── models/
│   └── display.py                  # Display-layer models (column definitions, sort specs)
│
└── portal/                         # Web portal (v0.2, empty in v0.1)
    └── __init__.py
```

### 2.3 CLI Framework Choice

**Decision: Typer**

| Option | Pros | Cons |
|---|---|---|
| **argparse** | stdlib, no dependency | Verbose, poor subcommand UX, no auto-completion |
| **Click** | Mature, widely used, composable | Manual type annotations, no auto-complete generation |
| **Typer** | Built on Click, type-hint driven, auto-complete, rich help | Extra dependency (though Hippo already uses Typer) |

Typer is selected because:
1. **Consistency** — Hippo's CLI already uses Typer (`hippo` command). Sharing the same
   framework reduces cognitive load for contributors and users.
2. **Type-hint driven** — Command signatures are plain Python functions with type annotations.
   This matches the SDK-first philosophy: CLI commands are thin wrappers over typed SDK calls.
3. **Auto-completion** — Typer generates shell completions (bash, zsh, fish) automatically.
   Entity type names and field names can be completed dynamically.
4. **Rich integration** — Typer integrates with the Rich library for styled terminal output
   (tables, progress bars, syntax highlighting) without additional plumbing.

### 2.4 Backend Integration Layer

The backend integration layer provides a uniform interface for CLI commands regardless of
whether Aperture is running in local or remote mode. This is not a heavy abstraction — it is
a thin protocol that keeps CLI command code free of mode-switching logic.

**`BackendProtocol`** (structural typing, not ABC):

```python
from typing import Protocol

class HippoBackend(Protocol):
    def list_entities(self, entity_type: str, filters: dict | None = None,
                      limit: int = 50, offset: int = 0) -> list[dict]: ...
    def get_entity(self, entity_type: str, entity_id: str) -> dict: ...
    def create_entity(self, entity_type: str, data: dict, actor: str) -> dict: ...
    def update_entity(self, entity_type: str, entity_id: str, data: dict,
                      actor: str) -> dict: ...
    def set_availability(self, entity_type: str, entity_id: str,
                         available: bool, actor: str) -> dict: ...
    def search(self, entity_type: str, query: str, field: str | None = None,
               limit: int = 10) -> list[dict]: ...
    def get_history(self, entity_type: str, entity_id: str) -> list[dict]: ...
    def list_entity_types(self) -> list[str]: ...
    def get_entity_type_schema(self, entity_type: str) -> dict: ...
    def status(self) -> dict: ...
```

**Two implementations:**

| Implementation | When used | How it works |
|---|---|---|
| `HippoSdkBackend` | Local mode (`hippo.mode: sdk`) | Instantiates `HippoClient` from a local `hippo.yaml`. All calls are in-process. |
| `HippoRestBackend` | Remote mode (`hippo.mode: rest`) | Calls Hippo REST API via `httpx`. Configured with `hippo.url`. |

Mode is determined by Aperture config:

```yaml
# aperture.yaml
hippo:
  mode: sdk          # "sdk" (local) or "rest" (remote)
  config: ./hippo.yaml  # SDK mode: path to hippo.yaml
  url: http://localhost:8000  # REST mode: Hippo server URL
```

When `mode: sdk`, Aperture imports `hippo` and instantiates `HippoClient` directly — no
network hop. When `mode: rest`, Aperture uses `httpx` to call the Hippo REST API.

**Fallback behavior:** If `mode` is not set, Aperture auto-detects: if a `hippo.yaml` exists
in the current directory or at `~/.bass/hippo.yaml`, use SDK mode. Otherwise, check for
`HIPPO_URL` environment variable and use REST mode. If neither is available, commands that
require Hippo print a clear configuration hint and exit.

### 2.5 Configuration

Aperture configuration follows the same pattern as Hippo: a single YAML file with environment
variable overrides.

```yaml
# aperture.yaml (or ~/.bass/aperture.yaml)
hippo:
  mode: sdk
  config: ./hippo.yaml

# Future v0.2 sections:
# cappella:
#   url: http://localhost:8001
# bridge:
#   url: http://localhost:9000
#   client_id: aperture-cli

output:
  format: table       # default output format: table | json | csv
  pager: auto          # auto | always | never
  color: auto          # auto | always | never
```

**Config resolution order** (highest priority first):
1. CLI flags (`--format json`)
2. Environment variables (`BASS_OUTPUT_FORMAT=json`)
3. Project config (`./aperture.yaml`)
4. User config (`~/.bass/aperture.yaml`)
5. Built-in defaults

### 2.6 CLI Command Tree (v0.1)

```
bass
├── list <entity_type>              # List entities (with optional filters)
│   ├── --filter key=value          # Filter by field value (repeatable)
│   ├── --limit N                   # Max results (default 50)
│   ├── --offset N                  # Pagination offset
│   ├── --format table|json|csv     # Output format
│   └── --include-unavailable       # Include unavailable entities
│
├── get <entity_type> <id>          # Get a single entity by UUID
│   └── --format table|json|csv
│
├── create <entity_type>            # Create entity (interactive or from JSON)
│   ├── --data '{"field": "value"}' # Inline JSON
│   ├── --file entity.json          # From file
│   └── --actor <identity>          # Actor identity (default: $USER)
│
├── update <entity_type> <id>       # Update entity fields
│   ├── --data '{"field": "value"}'
│   ├── --file patch.json
│   └── --actor <identity>
│
├── set-availability <entity_type> <id> <true|false>
│   └── --actor <identity>
│
├── search <entity_type> <query>    # Fuzzy search
│   ├── --field <field_name>        # Restrict to specific field
│   ├── --limit N
│   └── --format table|json|csv
│
├── history <entity_type> <id>      # Provenance history
│   └── --format table|json|csv
│
├── schema                          # Schema inspection
│   ├── list                        # List all entity types
│   └── show <entity_type>          # Show fields, relationships, validators
│
├── ingest <source> <file>          # Trigger batch ingestion (delegates to hippo ingest)
│   └── --actor <identity>
│
├── status                          # System status and connectivity check
│
└── config                          # Manage aperture.yaml
    ├── get <key>
    ├── set <key> <value>
    └── show                        # Print resolved config
```

### 2.7 Output Formatting

All commands pipe results through the `OutputFormatter`, which supports three modes:

| Format | Use case | Implementation |
|---|---|---|
| **table** | Interactive terminal use | Rich `Table` with auto-column-width, truncation, and color |
| **json** | Scripting, piping to `jq` | Raw JSON array/object, one entity per line with `--jsonl` |
| **csv** | Spreadsheet export, pipeline input | Standard CSV with header row |

**Column selection:** For table and CSV output, Aperture chooses sensible default columns per
entity type (id, key user-defined fields, availability). Users can override with
`--columns id,name,tissue_type`.

**Paging:** When output exceeds terminal height and `pager: auto` is set, Aperture pages
through a system pager (`$PAGER`, falling back to `less`). JSON output is never paged.

### 2.8 Auth Model

Aperture v0.1 does not implement authentication. It inherits the same no-op auth posture as
Hippo v0.1:

- **SDK mode:** No auth. The `actor` parameter on writes defaults to `$USER`.
- **REST mode:** No auth headers sent. Hippo REST v0.1 accepts all requests.

When Bridge is available (v0.2), Aperture will:
1. Acquire tokens via Bridge's auth endpoint (OAuth2 / device code flow for CLI).
2. Store tokens in `~/.bass/tokens.json` (encrypted at rest via OS keyring when available).
3. Attach `Authorization: Bearer <token>` to all REST requests.
4. Refresh tokens automatically before expiry.

Aperture will never implement its own user store or session management. Auth is Bridge's
responsibility. This decision aligns with the platform principle that each component has a
single, well-defined responsibility.

### 2.9 Error Handling

Aperture maps backend errors to user-friendly CLI output:

| Backend error | CLI behavior |
|---|---|
| `EntityNotFoundError` / HTTP 404 | Print `"Entity not found: <type> <id>"`, exit code 1 |
| `ValidationError` / HTTP 422 | Print validation errors as a bulleted list, exit code 1 |
| `AdapterError` / HTTP 500 | Print `"Backend error: <message>"`, suggest checking server logs, exit code 2 |
| Connection refused | Print `"Cannot connect to Hippo at <url>. Check configuration with 'bass config show'."`, exit code 2 |
| Auth failure (v0.2) | Print `"Authentication required. Run 'bass login'."`, exit code 3 |

All errors go to stderr. Normal output goes to stdout. This allows safe piping:
`bass list Sample --format json | jq '.[] | .name'`.

Exit codes:
- `0` — success
- `1` — user/data error (entity not found, validation failure)
- `2` — system error (connection failure, backend error)
- `3` — auth error (v0.2)

### 2.10 Dependencies

**Core CLI (v0.1):**

| Package | Purpose |
|---|---|
| `typer>=0.9` | CLI framework |
| `rich>=13.0` | Terminal formatting (tables, syntax highlighting, progress) |
| `httpx>=0.24` | HTTP client for REST mode |
| `pyyaml` | Config file parsing |
| `pydantic>=2.0` | Config validation and display models |

**SDK mode (optional install extra):**

| Package | Purpose |
|---|---|
| `hippo` | Hippo SDK for local mode |

**Installation extras:**

```bash
pip install bass-aperture              # CLI + REST mode (no local Hippo SDK)
pip install bass-aperture[local]       # Adds Hippo SDK for local mode
pip install bass-aperture[all]         # Everything including future portal deps
```

The base install (`bass-aperture`) does not depend on `hippo` — REST mode works without it.
The `[local]` extra adds the `hippo` package for SDK mode. This keeps the dependency footprint
small for users who connect to a remote Hippo instance.

### 2.11 Extensibility (Post-v0.1)

Aperture's architecture is designed to accommodate future extensions without restructuring:

| Extension | Integration point |
|---|---|
| **Cappella commands** (`bass resolve`, `bass reconcile`) | New command modules in `cli/commands/`, new `CappellaRestBackend` in `backends/` |
| **Web portal** | `portal/` package, consuming the same `backends/` layer |
| **Client libraries** | Thin wrappers over `backends/` with language-specific ergonomics |
| **Bridge auth** | `backends/auth.py` implements token acquisition/refresh; backends inject auth headers |
| **Custom commands** | Plugin entry point `aperture.commands` for site-specific CLI extensions |

### 2.12 Deployment Tiers

| Tier | Hippo mode | Auth | Transport | Typical use |
|---|---|---|---|---|
| **Laptop** | SDK (local `hippo.yaml` + SQLite) | None | None | Single researcher |
| **Team server** | REST (remote Hippo) | None (v0.1) / Bridge (v0.2) | HTTP | Small team |
| **Enterprise** | REST (remote Hippo via Bridge) | Bridge (OAuth2/JWT) | HTTPS | Institution-wide |

Aperture itself is always a client-side tool — there is no "Aperture server" in v0.1.
The web portal (v0.2) will require a lightweight server process, but all business logic
remains in the BASS component backends.

---
