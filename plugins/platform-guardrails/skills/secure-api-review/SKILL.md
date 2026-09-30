---
name: secure-api-review
description: >
  Apply the platform API-security standard. Use WHENEVER creating or modifying an
  external-facing or cross-service HTTP endpoint, writing/So changing an OpenAPI spec,
  adding a public route or a BFF/ACL surface, or reviewing API code. Triggers on words
  like endpoint, route, controller, handler, API, ingress, public surface.
---

# Secure API review

The authoritative sources are `.claude/rules/gitops.md`, `.claude/rules/qa-gate.md`, and
the memories `[[feedback_crossservice_m2m_auth_wiring]]`, `[[feedback_public_sso_app_forwardauth]]`.
This skill is the actionable checklist; when in doubt, the rule/memory wins.

When you create or change an endpoint, verify **all** of these — flag any you cannot satisfy:

1. **Authentication — no anonymous surface.** Every route is behind identity:
   - Public browser apps → Authentik forward-auth at the Ingress (SPA **and** its `/api`
     path). Verify an un-authenticated request `302`s to Authentik, never `200` — see
     `[[feedback_public_sso_app_forwardauth]]`.
   - Service→service → Authentik `client_credentials` JWT validated via JWKS; the 4
     must-align points (grant_types, signing-key/kid, consumer netpol, RFC3339 wire
     format) in `[[feedback_crossservice_m2m_auth_wiring]]`.
   - The only unauthenticated routes allowed are health/readiness (`/healthz`,
     `/actuator/health`). A public tokenised vendor route is a *credential*, not "no auth".
2. **Authorisation.** Enforce per-endpoint scope/role (401 vs 403 distinct). For a
   sensitive domain, gate the app to an Authentik **group** (PolicyBinding on the
   Application) — do not leave "any authenticated user".
3. **Input validation.** Validate every request body against the schema; reject unknown
   fields; bound string sizes (a bad/oversized/wrong-type input → **4xx, never 5xx**).
4. **Audit.** Every state-changing endpoint emits an audit event with **actor (from the
   verified identity, never a placeholder), action, entity, timestamp**. For regulated
   domains the audit log is append-only/immutable.
5. **Data classification.** Fields classed PII/secret must never appear in logs or error
   messages. Secrets come from Vault→ESO, never baked or returned.
6. **Egress / NetworkPolicy.** Default-deny egress; add explicit allows only for the real
   collaborators (DNS + the specific svc). A consumer that calls another service needs the
   matching netpol or it 500s in-pod (repro in-pod, not just in CI).
7. **Rate limiting** on public surfaces; **idempotency** on create/bind (Idempotency-Key,
   deterministic ids, no duplicate side-effects).
8. **Prove it live.** These are checked by the **QA gate** (`qa-gate.md`) against the
   running dev service before prod promotion — a mocked unit test cannot see an
   unauthenticated ingress or an RFC3339 wire-format mismatch. Contract-test every mocked
   boundary (testing.md L3).
