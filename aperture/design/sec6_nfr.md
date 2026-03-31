## 6. Non-Functional Requirements

**Depends on:** sec2 (architecture, backend integration layer), sec3 (CLI design, exit codes)
**Feeds into:** Implementation, acceptance testing

---

### 6.1 Performance

#### 6.1.1 Target workloads

Aperture v0.1 is a CLI tool — all performance targets concern **perceived command latency**
as experienced by a human at a terminal or a script waiting for output. There is no server
process; Aperture is a thin client.

| Mode | Backend | Typical user |
|---|---|---|
| **SDK mode** | In-process `HippoClient` against local SQLite | Single researcher, laptop |
| **REST mode** | HTTP to local or remote Hippo server | Small team, shared server |

#### 6.1.2 Startup latency

Python CLI startup (import time + config loading) dominates short commands like
`bass status` or `bass schema list`.

| Target | Value | Notes |
|---|---|---|
| `bass --help` time-to-output | < 300ms p95 | Pure Python import path; no backend contact |
| `bass status` (SDK mode) | < 1s p95 | Config load + HippoClient init + single ping |
| `bass status` (REST mode, local) | < 500ms p95 | Config load + one HTTP request |

Import optimisation techniques:
- Lazy-import the `hippo` SDK package — only import when a command that requires SDK mode
  is invoked. This keeps `bass --help` fast even when `hippo` is a large dependency.
- Lazy-import `rich` display components until first output is rendered.

#### 6.1.3 Command response targets

| Command | Mode | Target | Notes |
|---|---|---|---|
| `bass list <type>` (50 results) | SDK | < 200ms p95 | Hippo indexed query + table render |
| `bass list <type>` (50 results) | REST (local) | < 300ms p95 | HTTP round-trip + table render |
| `bass get <type> <id>` | SDK | < 100ms p95 | Single entity lookup |
| `bass get <type> <id>` | REST (local) | < 200ms p95 | |
| `bass search <type> <query>` | SDK | < 300ms p95 | Hippo FTS5 query |
| `bass history <type> <id>` | SDK | < 200ms p95 | Provenance event query |
| `bass schema list` | SDK | < 150ms p95 | Schema loaded at startup, no I/O |
| `bass ingest` (1000 rows) | SDK | < 35s | Delegates entirely to Hippo IngestionPipeline |

REST-mode targets assume a network RTT of < 5ms (local network). Remote (WAN) performance
is beyond Aperture's control and is not specified here.

#### 6.1.4 Output rendering

- Table rendering via Rich must not block: columns are determined from the first batch of
  results; streaming rendering is used for large result sets.
- JSON output is streamed to stdout without buffering the full result set in memory.
- CSV output is written row-by-row to stdout.
- The pager (`less`) is invoked only after all output has been rendered; Aperture does not
  hold a live backend connection while the user is paging.

---

### 6.2 Reliability and Error Recovery

#### 6.2.1 No partial writes on failure

The `bass create` and `bass update` commands delegate all writes to the Hippo SDK or REST
API. Hippo's transaction guarantees (sec2 §2.x) ensure atomicity. Aperture itself holds no
intermediate write state — it either receives a success response and prints the result, or
receives an error and prints the error. There is no partial-write scenario at the Aperture
layer.

#### 6.2.2 Interrupted ingestion

`bass ingest` processes a batch via Hippo's `IngestionPipeline`. If the command is interrupted
(Ctrl-C, SIGTERM):
- Records already committed by Hippo remain committed (Hippo handles atomicity per-record or
  per-batch depending on `on-conflict` mode).
- Aperture catches `KeyboardInterrupt` and prints a summary of how many records were processed
  before exit. Exit code 2.
- No rollback is attempted at the Aperture layer — operators must check the Hippo provenance
  log to determine which records were ingested.

#### 6.2.3 Idempotent config writes

`bass config set` writes only to the user config file (`~/.bass/aperture.yaml`). Multiple
invocations of the same `config set` produce the same result (idempotent). A temp-file +
rename pattern is used to prevent corrupting the YAML on write failure.

#### 6.2.4 Backend unavailability

If the configured Hippo backend is unavailable when a command requiring it is run:
- Error message printed to stderr with actionable hint (see sec3 §3.12).
- Exit code 2.
- No retry logic at the Aperture layer in v0.1. If the backend is down, the operator must
  bring it back up — Aperture does not queue or buffer operations.

---

### 6.3 Usability

#### 6.3.1 Time to first success

A new user with Python 3.10+ and a local Hippo instance should be able to run a successful
`bass list` within 5 minutes of installing `bass-aperture`, following only the output of
`bass --help` and `bass config show`.

This is an acceptance criterion, not a metric — it will be validated manually during QA.

#### 6.3.2 No silent failures

Every command that contacts a backend must either produce output or explain why it produced
none:
- Empty result set: `No Sample entities found matching the given filters.` (stdout, not stderr;
  exit code 0).
- Backend error: message to stderr; exit code ≥ 1.
- Invalid arguments: Typer's built-in usage message; exit code 2 (Typer default).

#### 6.3.3 Machine-readable output stability

`--format json` output is considered a **stable API surface** from v0.1 onward. Additive
changes (new keys) are backwards-compatible. Removing or renaming keys requires a major
version bump of `bass-aperture`.

`--format table` output is **not** considered stable — column names and widths may change
between minor versions. Scripts must use `--format json` or `--format csv`.

---

### 6.4 Security

#### 6.4.1 v0.1 posture

Aperture v0.1 has no auth layer. It inherits the no-auth posture of Hippo v0.1:
- SDK mode: actor is `$USER` by default. No credential validation.
- REST mode: no auth headers sent. Hippo REST v0.1 accepts all requests.

This is acceptable for single-researcher and small-team deployments where Hippo is
accessible only on a private network.

**Recommended deployment for v0.1:** Do not expose Hippo's REST API on a public network
without an external auth proxy. Aperture provides no protection against unauthenticated access.

#### 6.4.2 Config file permissions

The user config file (`~/.bass/aperture.yaml`) may contain sensitive values (e.g. a Hippo
URL on a private network). Aperture creates this file with mode `0600` (owner read/write only).
If the file is found with world-readable permissions, Aperture prints a warning:

```
Warning: ~/.bass/aperture.yaml is world-readable (mode 0644). Consider running:
  chmod 600 ~/.bass/aperture.yaml
```

#### 6.4.3 No credential storage in v0.1

Aperture v0.1 does not store API keys, tokens, or passwords anywhere. Token storage
(`~/.bass/tokens.json`, OS keyring integration) is a v0.2 concern (Bridge auth).

#### 6.4.4 Input handling

All entity data passed via `--data` flags is forwarded to Hippo as-is after JSON parsing.
Aperture does not execute or evaluate field values. Hippo's schema validation is the
authoritative input validation layer.

---

### 6.5 Observability

#### 6.5.1 Logging

Aperture uses Python's stdlib `logging` module. By default, only `WARNING` and above are
emitted to stderr. Debug logging is enabled with:

```bash
BASS_LOG_LEVEL=DEBUG bass list Sample
```

or:

```yaml
# aperture.yaml
logging:
  level: DEBUG   # DEBUG | INFO | WARNING | ERROR (default: WARNING)
```

Debug output includes:
- Backend mode detected (sdk or rest) and config source
- Each backend call made (method, arguments, duration)
- Config resolution trace (which file/env var supplied each key)

#### 6.5.2 `--verbose` flag

A `--verbose` / `-v` global flag enables `INFO`-level output: each backend call and its
duration is printed to stderr. This is distinct from `--format`; it does not change stdout
output.

```bash
bass list Sample --verbose
# stderr: [INFO] Backend: HippoSdkBackend (sdk mode, ./hippo.yaml)
# stderr: [INFO] list_entities(Sample, filters={}, limit=50) → 42 results in 87ms
# stdout: <table output>
```

---

### 6.6 Testability

#### 6.6.1 Backends are mockable

All CLI commands accept a backend object via dependency injection (not constructed internally).
This allows tests to pass a mock backend without monkeypatching imports:

```python
# In tests
from aperture.backends.base import HippoBackend
from unittest.mock import MagicMock

mock_backend = MagicMock(spec=HippoBackend)
mock_backend.list_entities.return_value = [{"id": "abc", "name": "S-001"}]

result = runner.invoke(app, ["list", "Sample"], obj={"backend": mock_backend})
```

#### 6.6.2 CLI output is deterministic for testing

- Table output has deterministic column ordering (schema field order, then system fields).
- JSON output is deterministic: keys are sorted alphabetically within each object.
- No timestamps or run-ids are embedded in command output.

#### 6.6.3 Exit codes are testable

All exit codes are documented and stable (sec3 §3.13). Tests must assert exit codes, not
just output content, to verify error-path behaviour.

---

### 6.7 Compatibility

#### 6.7.1 Python version

Minimum Python 3.10. Type hints (including `X | Y` union syntax) and `match` statements
are used throughout.

#### 6.7.2 Operating systems

Target: Linux (primary), macOS (supported), Windows (best-effort).

Windows notes:
- ANSI color codes are supported via `colorama` on Windows Terminal / PowerShell 7+.
  Older Windows consoles fall back to `--no-color` mode automatically.
- The pager on Windows defaults to `more` if `$PAGER` is not set. `less` is not bundled.
- Path separators in config files use `pathlib.Path` throughout; forward slashes accepted
  on all platforms.

#### 6.7.3 Terminal capabilities

Aperture auto-detects terminal capabilities via `rich.console.Console`:
- Color: disabled if `NO_COLOR` env var is set, or if stdout is not a TTY.
- Unicode: box-drawing characters in tables fall back to ASCII if the terminal does not
  support Unicode (detected via `TERM` and locale).
- Pager: disabled if stdout is not a TTY or `--no-pager` is set.

#### 6.7.4 Hippo version compatibility

Aperture v0.1 is pinned to Hippo v0.3+. The `HippoBackend` protocol (sec2 §2.4) defines the
minimum method surface required. If a Hippo instance returns an unexpected schema shape,
Aperture degrades gracefully:
- Missing fields in entity responses are rendered as `(none)` in tables and `null` in JSON.
- Unknown fields are passed through to JSON/CSV output without filtering.

---

### 6.8 Packaging and Distribution

| Target | Package | Install command |
|---|---|---|
| CLI + REST mode | `bass-aperture` | `pip install bass-aperture` |
| CLI + SDK mode | `bass-aperture[local]` | `pip install bass-aperture[local]` |
| All features | `bass-aperture[all]` | `pip install bass-aperture[all]` |

`pyproject.toml` entry point:

```toml
[project.scripts]
bass = "aperture.cli.main:app"
```

Shell completions are not installed automatically — users run `bass --install-completion`
after install.

---
