---
name: cilium-netpol
description: >
  Write NetworkPolicies that actually work on this Cilium cluster — especially letting a default-deny-egress
  pod reach the kube-apiserver, which a plain NetworkPolicy ipBlock CIDR does NOT match under Cilium. Use
  WHEN a pod in a locked-down namespace hangs on 10.43.0.1:443, wiring egress for a Job/CronJob that calls
  the API, an app can't reach its DB/Authentik/LiteLLM, or an ingress returns 504 to a healthy pod. Triggers
  on: NetworkPolicy, CiliumNetworkPolicy, default-deny, egress, kube-apiserver, toEntities, ipBlock, 504,
  netpol, Hubble.
---

# NetworkPolicies on Cilium (the gotchas that bite)

This cluster enforces policy with **Cilium**; the identity model is why a "correct-looking" k8s
NetworkPolicy silently fails. Rules: `gitops.md`, `conventions.md`; memory
[[feedback_cilium_apiserver_netpol]]. Observe actual drops in **Hubble UI**
(`https://hubble.10.0.0.200.nip.io`).

## #1 — kube-apiserver is an IDENTITY, not a CIDR
A standard `NetworkPolicy` with an `ipBlock` for the apiserver ClusterIP (`10.43.0.1/32`) does **NOT**
match under Cilium — so a **default-deny-egress** pod hangs forever on `10.43.0.1:443` (seen with CNPG
`initdb`, exec CronJobs). Two correct fixes:
- Prefer an **Ingress-only** default-deny (don't deny egress) if egress lockdown isn't required; **or**
- Use a **`CiliumNetworkPolicy`** with `toEntities`:
  ```yaml
  apiVersion: cilium.io/v2
  kind: CiliumNetworkPolicy
  spec:
    endpointSelector: {}            # or match the workload
    egress:
      - toEntities: [kube-apiserver]   # the apiserver identity (add `world` for off-cluster)
      - toEndpoints:                   # DNS
          - matchLabels: {k8s:io.kubernetes.pod.namespace: kube-system, k8s-app: kube-dns}
  ```
An **exec CronJob/Job** that talks to the API needs this `toEntities: [kube-apiserver]` too — a plain
netpol will make it hang ([[project_ktayl_itsm_glpi]]).

## #2 — an ingress 504 to a healthy pod = selector mismatch
The ingress→app netpol (and the Service) must select the pod by the **label the pod actually carries**.
In the GAP wrapper-chart, that's the **chart name, not the release name** — a netpol matching the release
name selects nothing → ingress-nginx can't reach the pod → **504** ([[feedback_wrapper_chart_dual_workload_bff]]).
Match `app: <chart-name>` (the subchart `selectorLabels`), confirm against `kubectl get pod --show-labels`.

## #3 — allow only what the app needs (default-deny + explicit allows)
LLM/data egress governance is enforced at L3/L4, not just config: a locked-down ns allows **DNS +
LiteLLM/Qdrant + same-ns datastores** and nothing else ([[feedback_llm_governance_egress_policy]]). Add
each real dependency (Authentik for OIDC/M2M, the DB `-rw` Service `:5432`, etc.) as an explicit egress
rule — a missing one shows as a silent timeout, visible as a drop in Hubble.

## Prod gating
`manifests/network-policies/*-prod.yaml` is CODEOWNERS-gated (gitops.md). Change via PR; verify the drop
is gone in Hubble and the pod reaches its dependency before declaring done.
