# Authentication & Access Control

Bridge manages all authentication and authorization for the BASS platform. This document
explains how credentials work, what roles are available, and how to set up access for your
team.

---

## How Authentication Works

All requests to the BASS platform go through Bridge. Bridge checks your credentials and
decides whether to forward the request to the appropriate component.

There are two types of credentials:

| Credential type | Best for | Lifetime |
|---|---|---|
| **API key** | Scripts, pipelines, CI/CD, notebooks | Long-lived (no expiry by default) |
| **JWT (login session)** | Interactive use via the CLI (`bass login`) or web portal | Short-lived (15 min access, 7 day refresh) |

---

## API Keys

### Creating an API key

```bash
# Create a key with analyst role
bass auth create-key --label "My notebook key" --role analyst

# Create a project-scoped key (can only access Lab A)
bass auth create-key --label "Lab A pipeline" --role analyst --project lab-a

# Create a key with an expiry date
bass auth create-key --label "Temp access" --role viewer --expires 2026-12-31
```

The key is printed **once** and cannot be retrieved again. Store it securely.

```
API key created successfully.

Key:   bass_live_7f3a8b2c4d5e6f1a2b3c4d5e6f7a8b9c...
Label: My notebook key
Role:  analyst
ID:    key_01jx...

Store this key now — it will not be shown again.
```

### Using an API key

Pass the key as a `Bearer` token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer bass_live_7f3a..." \
     https://bass.your-org.edu/api/v1/hippo/entities/sample
```

Or set it as an environment variable for the CLI and SDK:

```bash
export BASS_API_KEY=bass_live_7f3a...
bass entities list sample
```

```python
from hippo import HippoClient

client = HippoClient(url="https://bass.your-org.edu/api/v1/hippo", api_key="bass_live_...")
```

### Listing your keys

```bash
bass auth list-keys
```

### Revoking a key

```bash
bass auth revoke-key <key-id>
```

### Rotating a key

Rotation creates a new key and revokes the old one atomically. Old key stops working
immediately.

```bash
bass auth rotate-key <key-id>
```

---

## Interactive Login (CLI)

For interactive use, log in with your institutional account:

```bash
bass login
```

A browser window opens for authentication. After completing the login flow, your session
is saved to `~/.bass/tokens.json` (encrypted via your system keychain).

Subsequent `bass` commands use this session automatically. Sessions expire after 7 days;
`bass login` renews them.

```bash
# Check who you're logged in as
bass auth whoami

# Log out (revokes tokens)
bass logout
```

---

## Roles

Every user and API key has a role that determines what they can do:

| Role | What they can do |
|---|---|
| `admin` | Everything — manage users, schemas, API keys, all data |
| `project_lead` | Full data access and pipeline execution within their projects |
| `analyst` | Read/write entities and run pipelines within their projects |
| `viewer` | Read-only access within their projects |
| `service` | Machine identity for pipelines; scoped to specific operations |

Roles are assigned when a user is added to the platform or when an API key is created.
An API key's role cannot exceed the role of the user who created it.

---

## Projects and Access Scoping

Users with `analyst`, `viewer`, or `project_lead` roles can only access entities that
belong to their assigned projects. `admin` users can access all data regardless of project.

When an API key is created with `--project <name>`, it is further restricted to entities
in that specific project, even if the creating user has access to more projects.

Project membership is managed by the platform admin via:

```bash
bass admin projects add-member --project lab-a --user alice@uni.edu --role analyst
bass admin projects list-members --project lab-a
bass admin projects remove-member --project lab-a --user alice@uni.edu
```

---

## Security Best Practices

**API keys:**
- Use project-scoped keys for automated pipelines — a key that can only read/write one
  project limits the impact of a key leak.
- Use `viewer` role for read-only integrations (e.g., dashboards, reporting notebooks).
- Rotate keys that may have been exposed rather than leaving them active.
- Set an expiry date on temporary access keys.

**Secrets management:**
- Do not commit API keys to version control. Use environment variables or a secrets manager.
- The `bass_live_` prefix is public information; the full key is the secret. Keep the
  full key out of logs and error messages.

**Sharing access:**
- Give team members individual accounts rather than sharing a single API key. Individual
  accounts produce individually attributable provenance records and can be revoked
  independently.
