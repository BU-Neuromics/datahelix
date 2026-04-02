# Aperture CLI Quickstart

**Time:** ~10 minutes
**Goal:** Install `bass`, point it at a local Hippo instance, and query your first entity.

---

## Prerequisites

- Python 3.11+
- A running Hippo instance. If you don't have one, start one:

```bash
pip install hippo
hippo init --path ~/my_study
cd ~/my_study
hippo serve &   # starts on http://localhost:8001
```

---

## Step 1: Install Aperture

```bash
pip install bass-aperture
```

Verify the install:

```bash
bass --version
# bass 0.1.0
```

---

## Step 2: Configure

Point `bass` at your Hippo instance. By default, `bass` looks for `./aperture.yaml` in the
current directory, or `~/.config/bass/aperture.yaml` globally.

```bash
bass config set hippo.url http://localhost:8001
```

Confirm the configuration:

```bash
bass config show
# hippo:
#   url: http://localhost:8001
# output:
#   format: table
#   color: true
```

Alternatively, create `aperture.yaml` manually:

```yaml
hippo:
  url: http://localhost:8001
```

---

## Step 3: Check System Status

```bash
bass status
```

Expected output:

```
Component   Status    URL
──────────  ────────  ──────────────────────
hippo       ✓ online  http://localhost:8001
```

---

## Step 4: Inspect the Schema

List all entity types defined in your Hippo schema:

```bash
bass schema list
```

Example output (for an omics study):

```
Type               Fields  Required  References
─────────────────  ──────  ────────  ──────────
Donor              8       4         0
Sample             10      5         1 → Donor
SequencingDataset  12      6         2 → Sample, Donor
```

Show the fields for a specific type:

```bash
bass schema show Sample
```

```
Field           Type     Required  References
──────────────  ───────  ────────  ──────────
external_id     string   yes       —
name            string   yes       —
tissue          string   yes       —
diagnosis       string   no        —
donor_id        string   yes       → Donor
is_available    bool     yes       —
created_at      datetime yes       —
updated_at      datetime yes       —
```

---

## Step 5: List Entities

List the first 10 Donors:

```bash
bass list Donor --limit 10
```

```
external_id   name            diagnosis                          is_available
────────────  ──────────────  ─────────────────────────────────  ─────────────
SUBJ-001      John D., 67M    chronic traumatic encephalopathy   true
SUBJ-002      Jane M., 54F    control                            true
SUBJ-003      Robert K., 72M  chronic traumatic encephalopathy   true
```

Filter by field:

```bash
bass list Donor --filter diagnosis="chronic traumatic encephalopathy"
```

Output as JSON (for scripting):

```bash
bass list Sample --filter tissue=DLPFC --format json | jq '.[].external_id'
```

---

## Step 6: Get a Single Entity

```bash
bass get Donor SUBJ-001
```

```
Field            Value
───────────────  ──────────────────────────────────
external_id      SUBJ-001
name             John D., 67M
diagnosis        chronic traumatic encephalopathy
age_at_death     67
sex              M
is_available     true
created_at       2026-03-15T14:22:01Z
updated_at       2026-03-15T14:22:01Z
```

---

## Step 7: View Provenance

Every entity tracks a complete write history:

```bash
bass history Donor SUBJ-001
```

```
Timestamp             Event             Source         Field         Old → New
────────────────────  ────────────────  ─────────────  ────────────  ────────────────────────────
2026-03-15T14:22:01Z  created           csv_ingest     —             —
2026-03-16T09:11:43Z  field_updated     lims_sync      diagnosis     "control" → "chronic traumatic…"
```

---

## Step 8: Create an Entity

```bash
bass create Donor \
  --field external_id=SUBJ-010 \
  --field name="Alice W., 61F" \
  --field diagnosis=control \
  --field age_at_death=61 \
  --field sex=F
```

```
Created Donor SUBJ-010
```

---

## Next Steps

- **Ingest a CSV file:** `bass ingest --help`
- **Full command reference:** see [CLI Reference](cli-reference.md)
- **Deploy for a team:** see the [Platform Getting-Started Guide](../platform/getting-started.md)
- **Integrate with Cappella for external LIMS sources:** see the [STARLIMS Integration Guide](../cappella/docs/starlims-integration.md)
