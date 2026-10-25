---
name: authentik-app-onboarding
description: >
  Put an app behind Authentik the right way — native OIDC (the app speaks OIDC) OR machine-to-machine
  client-credentials (service→service), distinct from the forward-auth path for apps with no OIDC
  support. Use WHEN onboarding an app to SSO, wiring an OAuth2/OIDC provider+application in Authentik,
  a service that must call another service's protected API, or debugging a 401/invalid_token/JWKS bind.
  Triggers on: Authentik, OIDC, OAuth2 provider, client-credentials, M2M, JWKS, client_id/secret,
  SSO onboarding, invalid_token, groups claim, redirect_uri.
---

# Onboard an app to Authentik

Decide the integration shape first:

| App can speak… | Use | Skill |
|---|---|---|
| **OIDC/OAuth2** (login redirect) | **native OIDC** provider+application | this skill, §A |
| **nothing** (no auth) | **forward-auth** proxy provider at the ingress | `public-sso-app-forwardauth` |
| it's a **service calling another service** | **M2M client-credentials** | this skill, §B |

**Operate Authentik via the `ak-shell` ORM, not the API.** The Authentik API token path is dead on this
instance — create providers/applications/groups by mirroring an **existing working provider** through
`ak-shell` (Django ORM), exactly as the n8n/GLPI providers were made ([[feedback_public_sso_app_forwardauth]],
[[project_ktayl_itsm_glpi]]).

## §A — Native OIDC (user login)
1. **Provider** (OAuth2/OIDC): set `redirect_uris` to the app's callback; pick the **signing key**
   (note its `kid`). Scopes: `openid profile email` (+ `groups` if the app does role mapping).
2. **Application** bound to the provider; grant access via an Authentik **group↔application** policy
   (authorization is manual app↔group — [[feedback_homer_static_rbac_two_portals]]).
3. **App config**: issuer = `https://auth.10.0.0.200.nip.io/application/o/<slug>/`, client_id/secret from
   the provider → deliver the secret via **Vault→ESO** (`wire-vault-secret`), never a literal.
4. **Gotchas:** split-horizon — the app resolves the issuer to `10.0.0.200` and must **trust the minicloud
   CA** (CA-trust initContainer) ([[feedback_thirdparty_oidc_hardened_cluster]]); behind the ingress set
   `trust-proxy`/secure-cookie so the redirect keeps `https`; **groups** often arrive only if the
   passport/verify callback uses the right arity (the arity-5 fix — [[project_iam_deploy_specifics]]).

## §B — M2M client-credentials (service → service)
A caller gets a token from Authentik and the callee validates it against Authentik's JWKS. **Four things
must align or you get a silent 401/invalid_token** ([[feedback_crossservice_m2m_auth_wiring]]):
1. **`grant_types`** on the provider include `client_credentials`.
2. **Signing key / `kid`** the provider signs with == the key the consumer's JWKS validation expects.
3. **Consumer NetworkPolicy** actually allows egress to Authentik (and DNS) — a default-deny ns silently
   drops the token fetch.
4. **Wire-format**: timestamps the app sends must be **RFC3339** (a non-RFC3339 datetime got a `400` from
   policy-service — [[feedback_crossservice_m2m_auth_wiring]], testing.md L3).

Consumer auth config is often delivered via `envFrom` a Vault→ESO secret. **Reproduce a 500/401 in-pod**
(`kubectl --context minicloud exec`) against the real collaborator before assuming the provider is wrong —
a mocked boundary that was never contract-tested is the usual culprit (testing.md L3).

## Verify live
- OIDC: hit the app → 302 to `auth.…` → log in → lands back authenticated.
- M2M: in-pod `curl` the callee with a freshly-fetched token → 200; a 401 means one of the four above.
