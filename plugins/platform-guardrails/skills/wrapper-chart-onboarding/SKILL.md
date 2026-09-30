---
name: wrapper-chart-onboarding
description: >
  Deploy a custom-built service the GAP wrapper-chart golden-path way. Use WHEN
  onboarding a new custom service to the cluster, creating a services/<svc>/helm chart,
  adding a second workload (frontend/BFF) to a service, or debugging a wrapper-chart
  render. Triggers on: new service, helm chart, GAP, minicloud-app-deployment,
  values-dev/values-prod, releaseName, Chart.lock.
---

# Wrapper-chart onboarding (GAP golden path)

Authoritative source: `.claude/rules/gitops.md` (*Helm golden path — GAP wrapper-chart
standard*) + ADR `docs/helm-golden-path.md`. Reference impls: `services/ktayl-policy-service/helm`,
`services/ktayl-claims/helm` (dual-workload). This skill is the checklist + the traps.

A custom app is **its own thin Helm chart** that `dependencies:` on the shared library
chart `minicloud-app-deployment` (from `oci://ghcr.io/andrelair-platform`). ONE Helm
render, ONE ArgoCD Helm source — **no kustomize, no multi-source `$values`**.

## Steps
1. `services/<svc>/helm/Chart.yaml` — library dep, **version-pinned**; run
   `helm dependency update` → **commit `Chart.lock`** (ArgoCD repo-server runs
   `helm dependency build` to fetch it).
2. `values.yaml` (common: config under `minicloud-app-deployment:` + wrapper-local keys)
   + `values-dev.yaml` / `values-prod.yaml` (image.tag, hosts, replicas, prod-only gates).
3. Service-specific extras in `templates/` (DB StatefulSet, AnalysisTemplates, SSO
   Ingress, ES…). Env-varying ones read wrapper-local values; prod-only ones gated by a
   `.Values.<flag>.enabled`.
4. **Two ArgoCD apps** (dev+prod), single Helm source each, **`helm.releaseName: <svc>`**.
5. Add the namespaces to the AppProject. ghcr OCI is already a registered ArgoCD repo.
6. Kargo promotion = **yaml-update on `minicloud-app-deployment.image.tag`** — never a
   hand-edited tag (see the `prod-promotion-qa-gate` skill + `[[reference_kargo_promotion]]`).

## Traps that WILL bite (proven)
- **`.helmignore` must NOT contain `charts/`** — it makes helm treat the vendored dep as
  missing at render. Gitignore `charts/` instead; commit `Chart.lock`. (A hook refuses
  hand-edits to `charts/`.)
- **`helm.releaseName` is mandatory** — without it the workload/Service/Rollout take the
  ArgoCD *app* name (breaks selectors/netpols).
- **Escape non-Helm `{{ }}`** — ESO output-templates (`{{ .username }}`) and Argo-Rollouts
  analysis args must be backtick-wrapped `{{ ` … ` }}`. **No `{{ }}` in YAML comments either.**
- **Immutable selector = zero-downtime flip:** set subchart `selectorLabels: {app: <name>}`
  to MATCH the live Deployment/Rollout selector (in-place rolling update, not delete).
- **Dual workload (frontend/BFF):** alias the library subchart a second time
  (`frontend:` with `fullnameOverride`); the frontend is a BFF (server-side `API_URL` = the
  in-cluster svc, never the browser). Ingress netpol must match the **Service selector**
  (name=chart, not release) → else 504. See `[[feedback_wrapper_chart_dual_workload_bff]]`.
- **cert-manager issuer** = ClusterIssuer `minicloud-ca`; certs are **ECDSA/256** (Vault
  PKI is EC-only; a Gatekeeper policy DENIES RSA).

## Verify before PR
```bash
cd services/<svc>/helm && helm dependency update . && helm template <svc> . -f values-dev.yaml
```
Prereq: env-agnostic image (runtime config, never baked) — required for Kargo dev→prod.
