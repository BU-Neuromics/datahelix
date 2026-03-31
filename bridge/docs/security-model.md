# Security Model

This document describes what Bridge protects, how access control works end-to-end, and
what the audit trail covers.

---

## What Bridge Protects

Bridge is the authentication and authorization boundary for the BASS platform. After
deployment, **no component API (Hippo, Cappella, Canon) is accessible without a valid
credential**. Bridge validates every request before it reaches a component.

```
Internet / Lab network
        │
        ▼
  ┌─────────────┐
  │   Bridge    │  ← Only this port is externally accessible
  │  :8000      │
  └──────┬──────┘
         │ (validated requests only)
         ▼
┌────────────────────────────────────────┐
│  Internal network (not exposed)         │
│  Hippo :8001 | Cappella :8002 | Canon :8003 │
└────────────────────────────────────────┘
```

The components themselves do not perform credential validation. They trust the actor
identity that Bridge injects into each forwarded request.

---

## End-to-End Request Flow

When an API request arrives at Bridge:

1. **Extract credential** — from `Authorization: Bearer <token>` or `X-Api-Key: <key>`.
2. **Validate credential** — check JWT signature (or API key hash lookup).
3. **Check expiry / revocation** — expired and revoked credentials are rejected.
4. **Resolve role and project scope** — from JWT claims or API key metadata.
5. **Enforce RBAC** — check that the role permits the requested operation.
6. **Enforce project scope** — check that the actor is a member of the target project.
7. **Inject actor identity** — add `X-Bass-Actor` and `X-Bass-Roles` headers.
8. **Forward to component** — component processes the request and returns its response.
9. **Write audit record** — actor, method, path, response status, latency.

Steps 2–6 happen entirely within Bridge. The component only ever receives step 8.

---

## What the Audit Trail Covers

Bridge writes a structured audit log to track all security-relevant events.

### Auth events

| Event | Logged fields |
|---|---|
| Login (Device Code / Authorization Code) | actor, timestamp, IP, IdP provider |
| Login failure | reason, IP, timestamp |
| Token refresh | actor, token_id, timestamp |
| Token revocation | actor, token_id, reason, timestamp |
| API key creation | actor, key_id, label, role, project_scope, timestamp |
| API key revocation | actor, key_id, reason, timestamp |
| API key rotation | actor, old_key_id, new_key_id, timestamp |

### Request events (non-200)

For all non-successful requests, Bridge logs:

| Field | Description |
|---|---|
| `actor` | Authenticated identity (or `anonymous` for 401 failures) |
| `method` | HTTP method |
| `path` | Request path (query string omitted) |
| `status` | HTTP response status |
| `error_code` | Bridge error code (e.g., `insufficient_role`) |
| `latency_ms` | Total request duration |
| `request_id` | Unique request ID (matches `X-Bass-Request-Id` response header) |
| `timestamp` | UTC ISO-8601 |

Successful `GET` requests are not logged by default (configurable). Mutating requests
(`POST`, `PUT`, `PATCH`, `DELETE`) are always logged.

---

## What Is Not Protected

**SDK mode (local use) has no auth.** When using `HippoClient` directly in a Python
script or notebook (no Bridge, no REST API), there is no credential enforcement. This is
intentional — local single-user use should be frictionless.

**Bridge-to-component traffic is trusted.** Requests from Bridge to Hippo/Cappella/Canon
are not re-authenticated. Components accept `X-Bass-Actor` headers only from Bridge's
known network address. Ensure components are not accessible from outside the trusted
network.

---

## API Key Security Properties

- **Stored as hashes.** Bridge never stores the plaintext key. The full key is shown once
  at creation time and is unrecoverable after that.
- **Prefixed for environment detection.** `bass_live_` keys are for production; `bass_test_`
  keys are for staging. The prefix does not change security properties, but it prevents
  accidental cross-environment key use.
- **Role ceiling.** A key's role cannot exceed the role of the user who created it.
- **Project scope.** A project-scoped key cannot access data outside its assigned project,
  even if the creating user has broader access.

---

## JWT Security Properties

- **RS256 signing** in production (asymmetric key pair). Components can verify tokens
  without Bridge connectivity by caching the public key.
- **Short-lived access tokens** (15 minutes by default). A leaked access token has a
  bounded window of misuse.
- **Refresh token rotation.** Every refresh issues a new refresh token and invalidates
  the previous one. If a stolen rotated-out token is presented, Bridge revokes the
  entire token family and forces re-authentication.

---

## Multi-Tenant Isolation

In the initial platform version, all users share a single Bridge instance and Hippo
database. Isolation is enforced by **project scoping** — users can only see entities in
their assigned projects.

If your deployment requires stronger isolation (separate databases per lab, physical
separation of tenants), contact your platform admin to discuss deployment topology options.
Full multi-tenancy (isolated schemas or databases per tenant) is on the roadmap for a
future version.

---

## Reporting Security Issues

Found a security vulnerability in BASS? Please report it directly to the maintainers
rather than opening a public issue. See `SECURITY.md` in the repository root for the
responsible disclosure policy.
