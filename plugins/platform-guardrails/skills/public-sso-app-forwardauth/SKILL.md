---
name: public-sso-app-forwardauth
description: >
  Publish an app on a devandre.sbs subdomain behind Authentik forward-auth (SSO gate) via the
  Cloudflare tunnel. Use WHEN exposing an app publicly, SSO-gating an ingress, wiring Authentik
  forward-auth/proxy provider, or adding a tunnel route. Triggers on: forward-auth, public app,
  devandre.sbs, Authentik proxy, SSO gate, cloudflare tunnel, outpost, 302 gate.
---

# Publish a public app behind Authentik forward-auth

Authoritative constraints: `.claude/rules/workplace-architecture.md` (**every user-facing app MUST be
SSO-gated via Authentik — never "any authenticated user", group-gated**) + `.claude/rules/urls.md`
(the tunnel/ingress map). Controller/tunnel command specifics → the private `platform-ops-runbooks`
skill. Reference: [[feedback_public_sso_app_forwardauth]], [[feedback_thirdparty_oidc_hardened_cluster]].

## The shape
Browser → Cloudflare tunnel → ingress-nginx (forward-auth annotation) → Authentik outpost (SSO decision)
→ app. The app itself needn't speak OIDC — forward-auth gates it at the ingress. Prefer **native OIDC**
when the app supports it; use **forward-auth/proxy provider** when it doesn't.

## Steps
1. **Authentik provider+application** — create a **proxy provider** (forward-auth, single-app mode) + its
   application, bound to the embedded outpost. **The Authentik API token is dead** → do it via the
   **`ak shell` ORM** inside the server pod (mirror an existing provider, e.g. the n8n one), not the API.
2. **Group-gate it** — bind the application to the right Authentik group (`Direction <Dept>` / `Platform
   Admins`), never "any authenticated user". Membership lifecycle → `ktayl-iam`.
3. **Ingress** — add the forward-auth annotations (auth-url → the outpost, auth-signin → the AK host) +
   a `tls:` entry (every `devandre.sbs` host needs one). Native-OIDC apps on a hardened cluster also need
   the **CA-trust initContainer** (split-horizon → `10.0.0.200`, minicloud-CA) — see [[feedback_thirdparty_oidc_hardened_cluster]].
4. **Tunnel route** (cloudflared runs **in k8s**, NOT controller systemd):
   - DNS CNAME: `ssh controller "~/.local/bin/cloudflared tunnel route dns minicloud <app>.devandre.sbs"`
   - add the ingress rule to `manifests/cloudflare-tunnel/02-configmap.yaml` (PR, CODEOWNERS) → then
     `kubectl rollout restart deployment/cloudflared -n cloudflare-tunnel` (no hot-reload).
5. **Verify the gate BEFORE announcing** — an unauthenticated request must return **302 → SSO**, not 200.

## Gotchas
- **cloudflared is k8s, not the controller systemd unit** — editing `~/.cloudflared/config.yml` does NOTHING. The routes are the ConfigMap.
- A nip.io-only app path-exposed via the tunnel needs `httpHostHeader` (nginx routes on Host) — [[feedback_cloudflared_nip_only_ingress_hosthdr.md]].
- Gatekeeper `require-non-root` is a **hard deny** (ns-exemption, not a Checkov skip); use ghcr not lscr.io ([[feedback_thirdparty_oidc_hardened_cluster]]).
- `connect=000` immediately post-rollout is transient.
