---
name: wire-vault-secret
description: >
  Deliver a secret to a workload the platform way — Vault → External Secrets Operator (ESO)
  ExternalSecret → a Kubernetes Secret the pod consumes, never a committed literal. Use WHEN a
  new app needs a DB password / API key / dockerconfigjson, adding an ExternalSecret, wiring a
  ghcr imagePullSecret, or an app is OutOfSync/CreateContainerConfigError on a secret. Triggers
  on: Vault, ESO, ExternalSecret, imagePullSecret, ghcr-pull, dockerconfigjson, secret wiring,
  break-glass, CreateContainerConfigError, OutOfSync ExternalSecret.
---

# Wire a secret: Vault → ESO → pod

Authoritative rules: `gitops.md` (*ESO + ArgoCD SSA ignoreDifferences*, *Hybrid container registry*)
and `ops-runbooks.md` (*Controller Secret Hygiene*). Secrets are **never** committed — the Bash/Write
guards refuse literal key material. This skill is the how-to for the one correct path.

## The model (three tiers — pick the right one)
- **Runtime app secret** → **Vault** `secret/platform/<app>` → ESO renders a k8s Secret → pod. *This
  is the default and what this skill wires.*
- **Human break-glass** (emergency admin login when SSO is down) → **Vaultwarden** folder
  `controller-break-glass`. Not an ESO path.
- **Cold-start / cluster-recovery** → stays **off-cluster** (Vault + Vaultwarden run *on* the cluster).

## Steps (runtime app secret)
1. **Write the secret into Vault** (needs a token with write on the path — the Vault **root token**;
   the `platform/ghcr` read token cannot write). KV-v2:
   `vault kv put secret/platform/<app> username=… password=…`
2. **ExternalSecret** in the app's manifests (ns-scoped), referencing a `ClusterSecretStore`/`SecretStore`
   that points at Vault, with `target.name` = the Secret the pod mounts. Use an **output template** for
   composed values (e.g. a connection string, or a dockerconfigjson — see below).
3. **MANDATORY ArgoCD `ignoreDifferences`** on any Application that contains an ExternalSecret — ESO's
   webhook injects 4 fields at create time that are never in git, so the app sits permanently
   `OutOfSync` even while Healthy. Add exactly (and `RespectIgnoreDifferences=true`, or ArgoCD
   overwrites them in a loop → ESO re-injects forever):
   ```yaml
   ignoreDifferences:
     - group: external-secrets.io
       kind: ExternalSecret
       jqPathExpressions:
         - .spec.data[].remoteRef.conversionStrategy
         - .spec.data[].remoteRef.decodingStrategy
         - .spec.data[].remoteRef.metadataPolicy
         - .spec.target.deletionPolicy
   syncOptions:
     - RespectIgnoreDifferences=true   # alongside CreateNamespace/ServerSideApply
   ```
4. **Consume** in the pod: `envFrom`/`secretKeyRef`, or `imagePullSecrets` (below).

## ghcr image-pull secret (the common dockerconfigjson case)
Internal/Private ghcr packages need a pull secret. One shared `ghcr-pull` ExternalSecret **per namespace**
suffices (e.g. one in `ai` for agent+crew). Source = Vault `secret/platform/ghcr` (`username`,`token`);
render a `kubernetes.io/dockerconfigjson` via output template (`auth` = `printf "%s:%s" .username .token | b64enc`),
then add `imagePullSecrets: [ghcr-pull]` via a **prod-overlay patch**. The owning app needs the ESO
`ignoreDifferences` above if it uses ServerSideApply.

## Gotchas (each one has bitten this platform)
- **Silent no-op on a NEW ExternalSecret under auto-sync** — ArgoCD SSA can no-op the new `.spec.data`,
  keys never land → `CreateContainerConfigError`. Fix: **delete the ExternalSecret** so ESO recreates it
  fresh ([[feedback_argocd_externalsecret_ssa_noop]]).
- **Write needs the root token** — `secret/platform/ghcr`'s own token is read-only; minting a *write*
  path requires the Vault root token (ops-runbooks.md).
- **Not every admin login is in Vault** — some `secret/platform/*` entries hold runtime/robot/OIDC
  secrets, **not** the human admin password (e.g. `secret/platform/harbor` = core/jobservice/robot, not
  the admin login). The human break-glass source of truth is Vaultwarden.
- **CI dual-push secret trap** — a stale **repo-level** `HARBOR_USER`/`HARBOR_PASSWORD` shadows the
  org-level one (repo scope wins) → 401 at `docker login`. Check both `gh secret list --repo` and `--org`.
- **Verify live:** `kubectl --context minicloud get externalsecret -n <ns>` → `SecretSynced`, then the
  target Secret exists and the pod is past `CreateContainerConfigError`.
