---
name: prod-promotion-qa-gate
description: >
  Promote a custom service to prod the right way. Use BEFORE opening or approving any
  prod-promotion PR, when a service is live on dev and "ready for prod", or when wiring
  dev→prod promotion. Triggers on: promote to prod, prod PR, Kargo promotion, ready for
  production, QA gate, go-live.
---

# Prod promotion + QA gate

Authoritative: `.claude/rules/qa-gate.md`, `.claude/rules/testing.md`, `.claude/rules/gitops.md`
(*Kargo*), memories `[[feedback_full_ci_pyramid_before_prod]]`, `[[feedback_kargo_prod_promotion_discipline]]`,
`[[reference_kargo_promotion]]`. Order matters — do NOT skip a layer.

## The gate (in order — all must pass)
```
story built → CI L0–L4 GREEN → Kargo promotes to DEV → QA GATE (live, adversarial) → prod PR (CODEOWNERS)
```

1. **Full CI pyramid first, not L1-only.** A Tier-A service is NOT promotable on L0+L1.
   L2 (real DB/queue), L3 (contract against the *real* collaborator), L4 (smoke) must be
   green in CI. Every mocked boundary needs an L3/L2 test behind it — a mock is an
   assumption; an untested assumption ships green and fails in prod
   (`[[feedback_full_ci_pyramid_before_prod]]`).
2. **Live QA gate (L5) — mandatory, on the running dev pod.** Green CI is NOT sufficient
   (it can't see integration/deploy/runtime/config bugs). Run an **adversarial** pass
   against live dev covering the 12 areas in `qa-gate.md`: happy paths (every branch),
   input validation (4xx not 5xx), 404s, state/ordering guards (409 on terminal/locked),
   idempotency, boundaries, data integrity (money = minor units), **authz (is the ingress
   actually authenticated? actor attributed from identity?)**, malformed JSON → 4xx,
   **logs actually emitted in the pod**, dependency-down behaviour, domain invariants.
   **Blockers gate promotion.** Verify on the pod matching the **new image digest**
   (a rollout leaves old+new pods; a stale pod gives false results).
3. **Promote THROUGH Kargo — never a hand-edited tag.** Kargo owns the tag
   (`yaml-update` + `quote(...)`, which also dodges the all-digit-SHA YAML-number bug).
   Freight must be **dev-verified** before prod. The prod-stage Promotion opens a
   **CODEOWNERS PR** → **squash-merge** (`--squash`; a plain merge fails the signed-commit
   rule — Kargo commits are unsigned, squash creates one signed commit). ArgoCD then
   auto-syncs prod — **never `argocd app sync`** (a hook refuses it).
4. **After merge:** confirm ArgoCD `Synced/Healthy`, the pod is on the new digest, and
   re-run the QA smoke against live prod. Keep the QA harness in-repo (`tests/qa/`) so
   it's re-runnable every promotion (regression floor).

## Kargo Warehouse model (pick correctly)
- **image `NewestBuild`** only if the image build-timestamp is **monotonic per build**
  (epoch first-layer). Java/temurin or reproducible (fixed `config.created`) builds tie →
  NewestBuild silently stalls → use the **git model** (Freight = commit,
  `commitFrom("<repo>.git").ID[0:7]`). Multi-image services also need git (mixed-Freight
  bug). git model needs the phantom-commit guard (`excludePaths` mirrors CI `paths-ignore`).
  Details in `[[reference_kargo_promotion]]`.
