## 6. Platform Security Model

**Document status:** Draft v0.1 (2026-06-17)
**Depends on:** sec2_components.md (§2.6 Bridge — auth gateway), sec3_integration.md (§3.6 Bridge ↔ all components; auth middleware contract), `domain-graph.md` (knowledge-subgraph semantics), Hippo `sec8_auth_integration.md`, Bridge `sec4_auth.md`
**Feeds into:** Bridge `sec4_auth.md` (PDP engine), Hippo `sec4_api_layer.md` (filter pushdown), Aperture ADR-0007/0008/0011/0014/0016/0017/0018/0020 (capability-scoped client, deferred Bridge, BFF, provenance)

This section consolidates the platform-wide authorization model. It is the source of truth the
Aperture design references as `platform/design/sec6_security_model.md`. Where it conflicts with a
component-local statement, this document takes precedence (per the platform INDEX).

---

### 6.1 Purpose & scope

The platform must let a single enforcement point decide, per request, **what data a given viewer
may see** — at both record and field granularity — *without* teaching every component about
identity, credentials, or access rules. This section defines that model: who enforces, where, and
by what mechanism.

In domain-graph terms (see `domain-graph.md`), authorization is **subgraph restriction**: a query
conceptually returns a knowledge subgraph; enforcement prunes it to the **induced subgraph the
viewer is permitted to see** — dropping records they may not reach (record-level predicates) and
masking slots they may not read (field masks). The query surface is unchanged; only the returned
subgraph narrows.

Out of scope here: the wire-level auth mechanics (OAuth 2.0 / JWT / API keys / RBAC), which are
owned by Bridge `sec4_auth.md`; and bulk-payload (Canon/Cappella) access control, which follows
the same PEP/PDP model once the bulk-slice path exists (deferred with that path).

---

### 6.2 Principles

1. **Components hold no authority** (Aperture ADR-0008). A component never captures or carries its
   author's credentials or visibility. Its data reach is conferred by the **context it runs in**,
   resolved against the **current viewer** at call time, via an injected, capability-scoped client.
2. **Hippo is auth-unaware** (Hippo `sec8_auth_integration.md`). In SDK mode `HippoClient` accepts
   an `actor` string with no validation; in REST + Bridge mode Hippo reads a *validated* identity
   from Bridge-injected headers and trusts it unconditionally. Hippo holds no signing keys, user
   stores, or session tables.
3. **Centralized auth, decentralized enforcement is rejected for the data plane** — there is exactly
   **one** Policy Enforcement *and* Decision Point. Splitting PEP across components is the
   privilege-escalation surface this model exists to eliminate.
4. **SDK bypass is intentional.** Local single-user / SDK-mode deployments have no Bridge and no
   auth; that is the correct, frictionless posture for a researcher's laptop (Bridge `sec4_auth.md`
   §4.1). Auth applies only at the transport boundary.

---

### 6.3 Bridge is the sole PEP/PDP

**Bridge** is the platform's single Policy Enforcement Point and Policy Decision Point — the auth
gateway and unified-API integration middleware (see sec2 §2.6; Bridge `sec1`–`sec6`). For every
authenticated request it:

1. validates the caller's credential and resolves the **current viewer** (actor + roles);
2. decides the viewer's **record-level predicates** and **slot-level field masks** (the PDP);
3. builds a **capability-scoped client** carrying that decision and injects it downstream (the PEP);
4. forwards to the target component with a verified `X-Bass-Actor` / `X-Bass-Roles` identity
   (sec3 §3.6), strips internal prefixes, and aggregates health/observability.

Authorization never lives in Aperture or Hippo. The "thin BFF in front of Hippo" that a
multi-source, per-viewer model wants **is Bridge** (Aperture ADR-0014, ADR-0016): the BFF candidate
and the auth gateway are the same component.

---

### 6.4 The capability-scoped client (the enforcement seam)

The contract between the enforcement point and everything downstream is a single object: an
**injected, capability-scoped client** (Aperture ADR-0008). It is a `HippoClient`-shaped interface
that Bridge constructs *per request* and injects into the query context, auto-applying the viewer's
record-level predicates and slot-level field masks to every operation it serves.

- **Same interface, two implementations.** Locally it is a full-access / no-op pass-through;
  remotely it is the Bridge-built enforcing client. Aperture's generic GraphQL client — and every
  typed component running inside Aperture — **cannot tell the deployments apart** (Aperture
  ADR-0016).
- **The seam is present from day one** even though Bridge implementation is deferred (ADR-0016):
  all data access (Aperture's *and* its components') routes through the abstraction now, so
  introducing Bridge later is a **swap of the injected implementation, not a retrofit** — preserving
  the "safety universal from the first keystroke" invariant (ADR-0007) and avoiding a
  privilege-escalation retrofit across Aperture and every component.

---

### 6.5 One autogenerated GraphQL contract: local vs. Bridge

Aperture talks the **same autogenerated GraphQL contract** whether it points at Hippo directly
(local, no auth) or at Bridge (multi-user, enforcing). The **only** variable is the injected
capability-scoped client (§6.4). One reused GraphQL schema serves both deployments; enforcement is
a property of the injected client, never of the schema or of Aperture's call sites.

Consequence for consumers: a field that is **masked** (or a record excluded) must be treated as
**"not available," degrading gracefully** — consistent with resolved-relationship fields returning
`[]` today (Aperture ADR-0016, ADR-0010/0015). View binding must not assume every schema-declared
slot is present in a given viewer's result.

---

### 6.6 Enforcement mechanics: predicate pushdown + field masks

Two mechanisms, applied by the capability-scoped client, fully express the model:

| Mechanism | Granularity | Effect on the returned subgraph |
|---|---|---|
| **Record-level predicate pushdown** | which nodes/records | The viewer's permission predicates are pushed into the query as additional filters, so unauthorized records are never materialized — the result is the viewer's **induced subgraph**. |
| **Slot-level field masks** | which attributes | Slots the viewer may not read are masked out of each returned node — pruning attributes from the subgraph without changing its shape. |

This is enforced **at the query surface** so it composes with the uniform graph semantics of the
domain-graph model: restriction is just a narrower induced subgraph, not a special-cased code path.
Predicate pushdown depends on Hippo's filter expressiveness (notably set-membership / `IN`
filters — see §6.8).

---

### 6.7 Deployment postures

| Posture | Bridge | Auth | Capability-scoped client |
|---|---|---|---|
| **Local / SDK (single-user)** | none | none — trust-the-network / single user | full-access no-op pass-through |
| **Multi-user / institutional** | required | OAuth 2.0 + JWT / API keys / RBAC (Bridge `sec4_auth.md`) | Bridge-built enforcing client per request |

Near-term deployments are single-user / local and **not access-controlled** (Aperture ADR-0016):
demos must use non-sensitive data or be explicit that they are a trust-the-network deployment.
Field/slot-level masking arrives **with** Bridge.

---

### 6.8 Open work (tracked)

The enforcement *mechanism* (capability-scoped client; field mask + predicate pushdown; one reused
GraphQL schema) is settled. Remaining work, tracked outside this consistency pass:

- **PDP engine spike** — how Bridge computes a viewer's predicates + field masks from roles/policy
  (the decision half of the PEP/PDP). Drives a revision of Bridge `sec4_auth.md`.
- **Hippo `IN`-filter dependency** — record-level predicate pushdown needs set-membership filters
  in Hippo's query/GraphQL surface (today: equality + AND/OR + offset + FTS). Same capability-gap
  theme as the Aperture data-stories prefab (DS-2).
- **Bridge `sec4_auth.md` revision** — fold the capability-scoped-client construction and the
  header-injection contract into the auth spec.

Tracked in **hippo#54** and **drylims#27** (the auth issues). These are deliberately left to their
own sessions; this document defines the model, not the build.
