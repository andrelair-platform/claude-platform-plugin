---
name: kargo-warehouse-wiring
description: >
  Wire a custom service's Kargo Warehouse+Stages so dev→prod promotion is automatic and safe — and pick
  the IMAGE model vs the GIT model correctly (the NewestBuild monotonic-timestamp trap silently stalls
  promotion). Use WHEN onboarding a service to Kargo, a Warehouse stops producing Freight / nothing
  promotes, choosing image vs git Warehouse, a Java/reproducible-build image, or a multi-image service.
  Triggers on: Kargo, Warehouse, Freight, NewestBuild, allowTagsRegexes, promotion stalled, image vs git,
  ImagePullBackOff promotion, Stage, yaml-update.
---

# Wire a Kargo Warehouse (and choose image vs git)

Rules: `gitops.md` (*Multi-stage promotion — Kargo*); memories [[reference_kargo_promotion]],
[[feedback_kargo_prod_promotion_discipline]]. **Never hand-edit an image tag** — Kargo owns the bump; a
human editing `image.tag` is the anti-pattern this replaces. Division of labour: **CI builds & proves the
artifact; Kargo promotes it; ArgoCD deploys it.** A `services/<svc>/kargo/` dir is part of onboarding the
same day the service gets a dev deployment (auto-discovered by the `apps/platform/kargo-projects.yaml`
ApplicationSet). Four prerequisites: you build the image · dev+prod · env-agnostic (runtime config) ·
immutable SHA tag.

## Choose the Warehouse model — this is the decision that bites
**IMAGE model** (`imageSelectionStrategy: NewestBuild` + `allowTagsRegexes: [^[0-9a-f]{7,40}$]`) — only if
**ALL** hold: single image (or images that always change together) **AND** the image's build timestamp is
**monotonic per build**. Good for platform-demo / plane / agent / crew (first layer = epoch `1970-01-01`,
so Kargo falls back to a real `config.created`).

**GIT model** (a `git` subscription on the source repo `main`; Freight = a commit; Stage pins **all**
images to `${{ commitFrom("<repo>.git").ID[0:7] }}`) — use when **either**:
1. **multi-image** service where one image can be unchanged (two `NewestBuild` subs → **mixed Freight**,
   prod gets mismatched versions — retrieva), **or**
2. the image timestamp is **not monotonic** → NewestBuild silently can't rank → `FreightCreated=False
   "newest already exists"`, nothing promotes. Two causes: a **fixed base-layer date** (`FROM
   eclipse-temurin:21-jre` → same layer date every build — ktayl-claims) or a **reproducible build with a
   pinned `config.created`** (Go/distroless with fixed `SOURCE_DATE_EPOCH` — ktayl-policy-service).

**MANDATORY check before trusting the image model:**
```
kubectl --context minicloud get warehouse <w> -n <ns> -o json \
  | jq '.status.discoveredArtifacts.images[].references[].createdAt'
```
If the dates are **identical across different tags** → NewestBuild is broken → use the **git model**.
Do NOT hand-edit the dev tag to route around it — fix the Warehouse.

## Git-model required guards
- **Phantom-commit guard:** the git Warehouse makes Freight for *every* main commit, but CI skips
  docs-only commits (`paths-ignore: docs/** + *.md`) → promoting one → `ImagePullBackOff` (images never
  built). **Mirror the CI filter** on the subscription: `git.excludePaths: [docs, "regex:.*\\.md$"]`
  (make it a superset of CI's filter). The image model has no such gap.
- **Migrating image→git can't apply in place** (subscription-type change): after ArgoCD has the git spec,
  **delete the Warehouse** so selfHeal recreates it as git. The webhook defaults
  `git.commitSelectionStrategy` → keep it in the Warehouse `ignoreDifferences`.

## Promotion-value gotchas (both models)
- **Any value Kargo rewrites MUST be BLOCK-style YAML, never flow.** `image: { tag: "x" }` makes every
  promotion **Error** (`set-images … did not find expected ',' or '}'`) → silent hand-edit. Write
  `image:`⏎`  tag: "<sha>"` in **both** `values-dev.yaml` and `values-prod.yaml`. Never edit it with BSD
  `sed -i ''` (the Bash guard refuses this) — use the Edit tool.
- **Squash-merge Kargo PRs.** Kargo's promotion commits are unsigned but `main` requires verified
  signatures → `--merge` fails; `--squash` creates one signed commit. Dev auto-merge already uses squash;
  approve prod PRs with squash too.
- **Prod still goes through the QA gate + CODEOWNERS PR** — see `prod-promotion-qa-gate`. Kargo opens the
  prod PR; it is not auto-merged.

## Verify
`kubectl --context minicloud get freight,stage -n <ns>` → new Freight appears on a real build,
`verifiedIn:[dev]` before prod becomes promotable; the dev PR auto-merges (squash).
