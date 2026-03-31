## 5. API Client Libraries

**Depends on:** sec1 (scope decision — client libs deferred to v0.2), sec2 (backend integration layer, HippoBackend protocol)
**Feeds into:** Implementation (v0.2)

---

> **Status: Deferred to Aperture v0.2**
>
> Programmatic API client libraries (Python, R) are out of scope for v0.1. This
> section records design decisions that are already settled, constraints the v0.1
> implementation must not violate, and open questions to resolve when the v0.2
> spec is written.

---

### 5.1 Motivation

Bioinformaticians and data scientists frequently interact with BASS programmatically —
in Jupyter notebooks, R scripts, and pipeline code — rather than through a CLI or web UI.
Dedicated client libraries provide a more ergonomic experience than raw HTTP calls against
the Hippo REST API and avoid duplicating auth and error-handling logic across every caller.

---

### 5.2 Decisions Made (Binding for v0.1 Implementation)

| Decision | Choice | Rationale |
|---|---|---|
| When to deliver | v0.2 | v0.1 ships `HippoClient` (Hippo SDK) as the Python entry point; a separate `bass-aperture` client lib adds no value until more backends (Cappella, Bridge) exist |
| Python client entry point | `HippoClient` (from `hippo` package) is the v0.1 Python API | Aperture does not duplicate or wrap HippoClient; callers use it directly |
| Future Python client scope | A `bass` Python client will wrap Hippo + Cappella + Canon for unified multi-backend access | Not needed until v0.2 backend integrations exist |
| R client scope | Read-only (`bass_list`, `bass_get`, `bass_search`, manifest download) | R users are primarily consumers, not producers; write operations via R are low priority |
| Transport | REST only (no SDK mode for client libs) | Client libs always talk to a running platform over HTTP; SDK mode (in-process) is a developer/local-only deployment model |
| Auth | Client libs delegate to Bridge (v0.2) | No bespoke auth in client libs; Bridge tokens are injected at construction time |

---

### 5.3 `HippoClient` as v0.1 Python API

For v0.1, Python users who need programmatic access should use `HippoClient` directly:

```python
from hippo import HippoClient

client = HippoClient.from_config("./hippo.yaml")

# List entities
samples = client.list("Sample", filters={"tissue_type": "DLPFC"}, limit=100)

# Get single entity
sample = client.get("Sample", "abc123-...")

# Create entity
new_sample = client.put("Sample", {
    "name": "S-042",
    "tissue_type": "DLPFC",
    "donor_id": "D001"
}, actor="alice")

# Search
results = client.search("Sample", "frontal lobe")

# Provenance history
events = client.history("Sample", "abc123-...")
```

`HippoClient` is the canonical Python interface to Hippo and is documented separately
in the Hippo design spec (sec4 §4.x).

---

### 5.4 Anticipated Scope (v0.2)

**Python client (`bass-aperture[python]`):**

```python
from bass import BassClient

client = BassClient(url="http://bass.internal", token="...")

# Unified access across Hippo + Cappella
samples = client.hippo.list("Sample", filters={"tissue_type": "DLPFC"})
collection = client.cappella.resolve(criteria={...})
```

Key design goals for the v0.2 Python client:
- **Thin wrapper** over `HippoRestBackend` / `CappellaRestBackend` — no business logic
- **Pydantic models** for all entity types (generated from schema at import time or from a
  code-generation step in the build)
- **Async support** (`asyncio` / `httpx.AsyncClient`) as an optional extra
- **Pandas integration**: `client.hippo.list(...).to_dataframe()` returns a `pandas.DataFrame`

**R client (`bassR`):**

```r
library(bassR)

client <- bass_connect(url = "http://bass.internal", token = Sys.getenv("BASS_TOKEN"))

# Read operations
samples <- bass_list(client, "Sample", filter = list(tissue_type = "DLPFC"))
sample   <- bass_get(client, "Sample", "abc123-...")
manifest <- bass_download_manifest(client, collection_id = "col-xyz", format = "csv")
```

Key design goals for `bassR`:
- Read-only in v0.2 (list, get, search, manifest download)
- Returns `data.frame` / `tibble` by default
- Bioconductor-compatible (entity tables can be coerced to `SummarizedExperiment` metadata)
- No R-specific auth: token passed at construction or via `BASS_TOKEN` env var

---

### 5.5 Architectural Constraints for v0.1

1. **`HippoRestBackend` must be independently importable.** The REST backend in
   `backends/hippo_rest.py` must not import CLI-specific code. It should be usable as a
   standalone Python object for the future Python client.

2. **`BackendProtocol` is the contract.** The `HippoBackend` protocol defined in sec2 §2.4
   is the specification for what the v0.2 Python client will expose. Do not add CLI-only
   methods to the protocol.

3. **No generated code committed in v0.1.** Code generation for Pydantic models is a v0.2
   concern. v0.1 uses raw `dict` returns from all backend methods.

---

### 5.6 Open Questions (for v0.2 Spec)

| Question | Priority | Notes |
|---|---|---|
| Code generation for entity models (Pydantic): at install time or at publish time? | High | Install-time gen requires a running Hippo instance; publish-time gen requires schema versioning. |
| Should `bassR` use `httr2` or `curl`? | Medium | `httr2` is modern and composable; `curl` has fewer dependencies. |
| Async Python client: first-class or optional extra? | Medium | Depends on adoption; async is needed for Jupyter async notebooks. |
| Bioconductor submission for `bassR`? | Low | High value for the genomics community but significant maintenance burden. |
| MATLAB client? | Low | Some imaging labs use MATLAB; read-only wrapper around REST is feasible but low priority. |

---
