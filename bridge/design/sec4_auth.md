## 4. Authentication & Authorization

**Document status:** Draft v0.1
**Depends on:** Hippo sec2 (auth middleware stub, actor field), Hippo sec6 (provenance event model), Aperture sec2 (auth model / token expectations)
**Feeds into:** Bridge sec2 (architecture), Bridge sec3 (unified API), Aperture sec2 (auth integration), all component deployment docs

---

### 4.1 Design Philosophy

Bridge owns all authentication and authorization for the DataHelix platform. Individual components
(Hippo, Cappella) are auth-unaware by design — they accept a validated `actor` identity from
their transport layer and trust it unconditionally. Bridge sits in front of component REST APIs
as the single enforcement point:

1. **Centralized auth, decentralized enforcement** — Bridge validates credentials and injects
   a verified actor identity. Component auth middleware stubs (e.g., Hippo's `AuthMiddleware`
   ABC) are replaced by Bridge-aware implementations that extract the validated identity from
   request context rather than performing their own credential checks.

2. **No component user stores** — Components never maintain user databases, session tables, or
   credential stores. All identity resolution flows through Bridge.

3. **SDK bypass is intentional** — When components are used in SDK mode (e.g., local
   `HippoClient` with SQLite), there is no Bridge and no auth. This is the correct posture for
   single-user local deployments. Auth applies only at the transport layer boundary.

4. **Standards-based** — Bridge uses widely adopted standards (OAuth 2.0, JWT, RBAC) to
   minimize custom security code and maximize interoperability with institutional identity
   providers.

---

### 4.2 Authentication Standards

#### 4.2.1 Primary: OAuth 2.0 + JWT

Bridge uses **OAuth 2.0** as the authorization framework and **JWT (RFC 7519)** as the token
format. This combination was chosen because:

- OAuth 2.0 is the dominant standard in both enterprise and research computing environments
- JWTs are stateless and can carry claims (roles, scopes) that downstream components inspect
  without calling back to Bridge
- Broad library support in Python (`PyJWT`, `authlib`) and every other language

**Supported OAuth 2.0 flows:**

| Flow | Use Case | Client Type |
|---|---|---|
| Authorization Code + PKCE | Web portal (Aperture web UI) | Public client (browser) |
| Device Code (RFC 8628) | CLI tools (Aperture CLI, `datahelix` command) | Public client (terminal) |
| Client Credentials | Service-to-service (Cappella → Hippo, pipeline agents) | Confidential client |

SAML 2.0 is **not** natively supported. Institutions requiring SAML can federate through their
IdP's OAuth 2.0 bridge (e.g., Shibboleth with OAuth proxy, Azure AD). This avoids the
complexity of maintaining a SAML SP implementation while remaining compatible with the academic
identity ecosystem.

#### 4.2.2 Identity Provider Integration

Bridge acts as an **OAuth 2.0 client** to external Identity Providers (IdPs), not as an IdP
itself. Supported IdP configurations:

| Provider Type | Examples | Protocol |
|---|---|---|
| Institutional IdP | Azure AD, Okta, Auth0, Keycloak | OIDC (OpenID Connect) |
| Academic federation | CILogon, InCommon | OIDC via CILogon proxy |
| Local dev/test | Bridge built-in provider | OAuth 2.0 (local-only) |

```
┌────────────┐     ┌─────────────────┐     ┌────────────────┐
│  Aperture   │────▶│     Bridge      │────▶│  External IdP  │
│  (CLI/Web)  │◀────│  (OAuth Client) │◀────│  (OIDC Server) │
└────────────┘     └────────┬────────┘     └────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │  JWT issued by    │
                  │  Bridge (signed)  │
                  └───────────────────┘
```

After external authentication, Bridge issues its own **signed JWT** with DataHelix-specific claims.
Components never interact with external IdP tokens directly.

#### 4.2.3 Token Structure

Bridge-issued JWTs contain the following claims:

| Claim | Type | Description |
|---|---|---|
| `sub` | string | Unique user identifier (Bridge user ID, UUID) |
| `iss` | string | `datahelix-bridge` (fixed issuer) |
| `aud` | string | `datahelix-platform` (or component-specific audience for scoped tokens) |
| `exp` | int | Expiry timestamp (UTC epoch) |
| `iat` | int | Issued-at timestamp |
| `jti` | string | Unique token ID (for revocation checking) |
| `datahelix:actor` | string | The actor identity string passed to component `actor` fields |
| `datahelix:roles` | string[] | RBAC roles assigned to this user (see §4.3) |
| `datahelix:scopes` | string[] | OAuth scopes granted in this session |
| `datahelix:org` | string | Organization/tenant identifier (multi-tenant deployments) |

The `datahelix:actor` claim is the canonical link between Bridge auth and Hippo provenance — it
becomes the `actor` field on all provenance events, ensuring an unbroken audit trail from
login through every data mutation.

---

### 4.3 Role-Based Access Control (RBAC)

#### 4.3.1 Role Model

Bridge implements a **flat RBAC model** (no role hierarchy in v0.1) with the following
predefined roles:

| Role | Description | Typical Persona |
|---|---|---|
| `admin` | Full platform access; manage users, roles, and configuration | Platform administrator |
| `project_lead` | Full data access within assigned projects; manage project membership | PI, lab manager |
| `analyst` | Read/write entities and run pipelines within assigned projects | Bioinformatician, data scientist |
| `viewer` | Read-only access to entities and pipeline results within assigned projects | Collaborator, auditor |
| `service` | Machine identity for pipelines and automated processes | Cappella runner, ingestion agent |

Roles are assigned per-user. Project scoping (which projects a user can access) is a separate
dimension — see §4.3.3.

#### 4.3.2 Permission Matrix

Permissions map roles to operations on DataHelix resources:

| Operation | `admin` | `project_lead` | `analyst` | `viewer` | `service` |
|---|---|---|---|---|---|
| **Entity CRUD** (create, read, update) | ✅ | ✅ (own projects) | ✅ (own projects) | read only | ✅ (scoped) |
| **Entity availability change** | ✅ | ✅ (own projects) | ❌ | ❌ | ❌ |
| **Schema management** (upload, migrate) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Pipeline execution** (submit, cancel) | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Pipeline results** (read) | ✅ | ✅ | ✅ | ✅ | ✅ (own) |
| **Provenance read** (history, audit log) | ✅ | ✅ (own projects) | ✅ (own projects) | ✅ (own projects) | ❌ |
| **User/role management** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **API key management** (create, revoke) | ✅ | own keys only | own keys only | ❌ | N/A |
| **Reference data install** | ✅ | ✅ | ❌ | ❌ | ✅ |

#### 4.3.3 Project Scoping

Non-admin roles are scoped to **projects** — a lightweight grouping concept managed by Bridge:

- A project has a name, description, and a set of member-role assignments
- Entity types in Hippo can optionally declare a `project` field; Bridge enforces that
  non-admin users can only access entities belonging to their assigned projects
- When a project field is not declared in the schema, project scoping is disabled and all
  authenticated users with the appropriate role can access all entities
- `admin` users bypass project scoping entirely

```
┌──────────────────────────────────────────────┐
│  Bridge Project: "Genomics Lab A"            │
│                                              │
│  Members:                                    │
│    alice@uni.edu   → project_lead            │
│    bob@uni.edu     → analyst                 │
│    pipeline-agent  → service                 │
│                                              │
│  Scoped to: entities where project =         │
│             "genomics-lab-a"                  │
└──────────────────────────────────────────────┘
```

#### 4.3.4 Future: Hierarchical Roles and Custom Permissions

v0.1 uses a flat role model for simplicity. Future versions may add:
- Role hierarchy (e.g., `project_lead` inherits all `analyst` permissions)
- Custom permission definitions per deployment
- Attribute-based access control (ABAC) for fine-grained entity-level rules

These are explicitly deferred. The flat model covers the common cases for academic and small
institutional deployments.

---

### 4.4 Token Management and Session Handling

#### 4.4.1 Token Lifecycle

```
┌──────────┐  authenticate  ┌─────────┐  issue tokens  ┌──────────────┐
│  Client   │──────────────▶│  Bridge  │───────────────▶│ Access Token │
│ (Aperture)│               │  Auth    │                │ (JWT, 15min) │
└──────────┘               │  Service │                ├──────────────┤
                            │          │───────────────▶│Refresh Token │
                            └─────────┘                │ (opaque, 7d) │
                                                       └──────────────┘
```

| Token Type | Format | Lifetime | Storage |
|---|---|---|---|
| Access token | JWT (signed, not encrypted) | 15 minutes (configurable) | In-memory only; never persisted by client |
| Refresh token | Opaque string (UUID) | 7 days (configurable) | Client: `~/.datahelix/tokens.json` (encrypted via OS keyring). Bridge: hashed in token store |
| API key | Opaque string (prefixed `datahelix_`) | No expiry (revocable) | Client: environment variable or config file. Bridge: hashed in key store |

#### 4.4.2 Token Refresh

Aperture (and other clients) refresh tokens automatically before access token expiry:

1. Client detects access token will expire within 60 seconds
2. Client sends refresh token to `POST /bridge/auth/token/refresh`
3. Bridge validates refresh token, issues new access + refresh token pair
4. Old refresh token is invalidated (rotation)

Refresh token rotation ensures that a leaked refresh token can only be used once before
detection. If a rotated-out refresh token is presented, Bridge revokes the entire token
family and forces re-authentication.

#### 4.4.3 Token Revocation

- Individual tokens: `POST /bridge/auth/token/revoke` (by `jti` or refresh token)
- All user tokens: `POST /bridge/auth/users/{userId}/revoke-all` (admin only)
- Revocation is checked via a short-lived revocation cache (in-memory set of revoked `jti`
  values, synced from the token store). Because access tokens are short-lived (15min), the
  revocation window is bounded.

---

### 4.5 Integration with Hippo Provenance

Bridge auth integrates with Hippo's provenance system through the `actor` field:

#### 4.5.1 Actor Identity Flow

```
┌──────────┐     ┌─────────┐     ┌──────────────┐     ┌─────────────┐
│  Client   │────▶│  Bridge │────▶│  Hippo REST  │────▶│  Provenance │
│           │     │         │     │              │     │  Event      │
│  JWT with │     │ Extract │     │ auth.py uses │     │             │
│ datahelix:actor│     │ actor   │     │ actor from   │     │ actor =     │
│           │     │ claim   │     │ request ctx  │     │ "alice@     │
│           │     │         │     │              │     │  uni.edu"   │
└──────────┘     └─────────┘     └──────────────┘     └─────────────┘
```

1. Bridge extracts the `datahelix:actor` claim from the JWT
2. Bridge injects the actor identity into the proxied request (via `X-DataHelix-Actor` header
   or request body override)
3. Hippo's `AuthMiddleware` implementation (Bridge-aware) reads the injected actor and
   uses it for all provenance events
4. The actor value in provenance is always the authenticated identity — callers cannot
   override it when Bridge is active

#### 4.5.2 Service Account Actors

Service accounts (role `service`) produce provenance events with actor values like
`service:cappella-runner` or `service:ingestion-agent-01`. These are distinguishable from
human actors by the `service:` prefix convention.

#### 4.5.3 Provenance Query Authorization

Bridge enforces that provenance history queries respect project scoping:
- Users can only view provenance events for entities in their assigned projects
- `admin` users can view all provenance events
- The `viewer` role can read provenance but not trigger mutations

---

### 4.6 API Key Management

API keys provide long-lived authentication for non-interactive use cases (scripts, pipeline
agents, CI/CD integrations).

#### 4.6.1 Key Structure

```
datahelix_live_7f3a8b2c4d5e6f...    (production key)
datahelix_test_9a1b2c3d4e5f6a...    (test/staging key)
```

Keys are prefixed with `datahelix_live_` or `datahelix_test_` to prevent accidental cross-environment
use. The prefix is not secret — it aids in key identification and rotation auditing.

#### 4.6.2 Key Lifecycle

| Operation | Endpoint | Who Can Do It |
|---|---|---|
| Create key | `POST /bridge/auth/api-keys` | `admin`, or user creating own key (`project_lead`, `analyst`) |
| List keys | `GET /bridge/auth/api-keys` | Own keys, or all keys for `admin` |
| Revoke key | `DELETE /bridge/auth/api-keys/{keyId}` | Key owner or `admin` |
| Rotate key | `POST /bridge/auth/api-keys/{keyId}/rotate` | Key owner or `admin` |

Keys are created with:
- A human-readable **label** (e.g., "Cappella pipeline runner")
- An optional **expiry date** (no expiry by default)
- An assigned **role** (cannot exceed the creating user's role)
- Optional **project scope** (limits key to specific projects)

#### 4.6.3 Key Authentication Flow

When a request arrives with an API key (via `Authorization: Bearer datahelix_live_...` or
`X-Api-Key` header):

1. Bridge hashes the key and looks it up in the key store
2. If found and not revoked/expired, Bridge constructs an equivalent JWT claim set from the
   key's metadata (role, scopes, actor identity)
3. Downstream processing is identical to JWT-authenticated requests — components see no
   difference

---

### 4.7 Service-to-Service Authentication

Internal communication between DataHelix components (e.g., Cappella calling Hippo to register
pipeline outputs) uses the **Client Credentials** OAuth 2.0 flow:

#### 4.7.1 Service Registration

Each component that needs to call other components registers as an OAuth client with Bridge:

| Service | Client ID | Default Role | Purpose |
|---|---|---|---|
| Cappella | `cappella-engine` | `service` | Register pipeline outputs in Hippo |
| Aperture (web portal) | `aperture-portal` | N/A (acts on behalf of users) | Backend-for-frontend |
| Custom pipeline agents | Per-agent registration | `service` | Automated data ingestion |

#### 4.7.2 Internal Token Flow

```
┌──────────┐  client_credentials  ┌─────────┐  service JWT  ┌───────┐
│ Cappella  │────────────────────▶│  Bridge  │─────────────▶│ Hippo │
│           │    (client_id +     │  Auth    │              │       │
│           │     client_secret)  │          │              │       │
└──────────┘                     └─────────┘              └───────┘
```

Service tokens are short-lived (5 minutes) and scoped to the specific operations the service
needs. Service secrets are provisioned at deployment time and stored in the platform's secret
manager (e.g., AWS Secrets Manager, Vault, or environment variables for local deployments).

---

### 4.8 Deployment Configuration

#### 4.8.1 Bridge Auth Configuration (`bridge.yaml`)

```yaml
auth:
  # JWT signing
  jwt:
    algorithm: RS256                    # RS256 recommended; HS256 for local dev
    signing_key: ${BRIDGE_JWT_KEY}      # Path to PEM private key or inline HMAC secret
    public_key: ${BRIDGE_JWT_PUB_KEY}   # Path to PEM public key (RS256 only)
    access_token_ttl: 900              # seconds (15 min default)
    refresh_token_ttl: 604800          # seconds (7 day default)

  # Identity provider
  idp:
    provider: oidc                     # oidc | local
    issuer_url: https://idp.uni.edu    # OIDC discovery endpoint
    client_id: ${BRIDGE_OIDC_CLIENT}
    client_secret: ${BRIDGE_OIDC_SECRET}

  # Token storage (refresh tokens, revocations)
  token_store:
    backend: sqlite                    # sqlite | postgresql | redis
    connection: ${BRIDGE_TOKEN_DB}

  # API key storage
  api_key_store:
    backend: sqlite                    # sqlite | postgresql
    connection: ${BRIDGE_APIKEY_DB}

  # Built-in local provider (dev/test only)
  local_provider:
    enabled: false
    users:
      - username: admin
        password: ${BRIDGE_LOCAL_ADMIN_PW}
        roles: [admin]
      - username: testuser
        password: ${BRIDGE_LOCAL_TEST_PW}
        roles: [analyst]
```

#### 4.8.2 Deployment Tiers

| Tier | IdP | JWT Algorithm | Token Store | Key Store |
|---|---|---|---|---|
| **Local dev** | Built-in local | HS256 | SQLite | SQLite |
| **Team server** | Keycloak / Auth0 | RS256 | SQLite or PostgreSQL | SQLite or PostgreSQL |
| **Enterprise** | Institutional OIDC (Azure AD, Okta) | RS256 | PostgreSQL or Redis | PostgreSQL |

All tiers use the same Bridge codebase. Tier is determined entirely by `bridge.yaml`
configuration.

---

### 4.9 Component Auth Integration Points

This section documents how each DataHelix component integrates with Bridge auth:

#### 4.9.1 Hippo

- **Middleware replacement:** Hippo's `AuthMiddleware` ABC (defined in `hippo/rest/auth.py`)
  receives a Bridge-aware implementation that extracts `X-DataHelix-Actor` and `X-DataHelix-Roles`
  headers from proxied requests
- **`authenticate()`:** Returns the actor identity from `X-DataHelix-Actor` (validated by Bridge
  before the request reaches Hippo)
- **`authorize()`:** Checks the operation against the role permissions in `X-DataHelix-Roles`.
  Because Bridge has already validated the JWT and injected headers, Hippo does not need JWT
  libraries or signing keys
- **SDK mode:** No change — `HippoClient` accepts `actor` as a string parameter with no
  validation, as designed in Hippo sec2 §2.7

#### 4.9.2 Cappella

- **Pipeline submission:** Cappella validates the caller's JWT (forwarded by Bridge) to ensure
  the `analyst` or `service` role before accepting pipeline execution requests
- **Output registration:** Cappella uses its service credential (Client Credentials flow) to
  write pipeline results back to Hippo through Bridge

#### 4.9.3 Aperture

- **CLI:** Uses Device Code flow. On first use, `datahelix login` opens a browser for
  authentication. Tokens stored in `~/.datahelix/tokens.json` (encrypted via OS keyring)
- **Web portal:** Uses Authorization Code + PKCE flow. Session managed by Aperture's BFF
  (backend-for-frontend) server
- **Token refresh:** Handled transparently by Aperture's `backends/auth.py` module (see
  Aperture sec2 §2.8)

---

### 4.10 Security Considerations

| Concern | Mitigation |
|---|---|
| JWT signing key compromise | Use RS256 with hardware-backed keys in production; rotate annually |
| Refresh token theft | Rotation on every use; stolen rotated token triggers family revocation |
| API key leakage | Prefixed keys for environment detection; hash-only storage; revocation API |
| Privilege escalation | API keys cannot exceed creator's role; no self-promotion |
| Cross-site attacks (web portal) | PKCE for all browser flows; `SameSite=Strict` cookies; CORS allowlist |
| Service credential compromise | Short-lived service tokens (5min); secrets in dedicated secret manager |
| Actor identity spoofing | `X-DataHelix-Actor` header only accepted from Bridge's internal network; components reject it from external sources |

---

### 4.11 Open Questions

| Question | Priority | Notes |
|---|---|---|
| Should Bridge support LDAP directly for institutions without OIDC? | Medium | Current position: no — use OIDC proxy. May revisit if adoption blocked |
| Fine-grained entity-type permissions (e.g., can edit Sample but not Subject) | Medium | Deferred to v0.2; current RBAC is operation-level, not entity-type-level |
| Multi-tenant isolation model (shared vs. siloed token stores) | High | Relevant for SaaS deployment; deferred until multi-tenancy is scoped |
| Offline token validation (JWT verification without Bridge connectivity) | Low | JWTs are self-contained by design; document the offline-capable pattern |
| Audit log for auth events (login, token refresh, key creation) | Medium | Should feed into Bridge's own event log, separate from Hippo provenance |
