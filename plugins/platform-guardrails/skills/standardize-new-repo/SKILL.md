---
name: standardize-new-repo
description: >
  Standardise a newly created custom-built repo to the house baseline before its first
  story merges to main. Use WHEN creating a new product/service repo, setting up its
  GitHub About/README/LICENSE/CONTRIBUTING, wiring release-please, or checking a repo is
  onboarding-complete. Triggers on: new repo, repo standardization, README template,
  release-please, gh api About, CONTRIBUTING, LICENSE, onboard repo, first service.
---

# Standardise a new repo (the pre-S001 baseline)

Authoritative source: `.claude/rules/conventions.md` (*Repo standardisation* + *Automated releases*) +
`.claude/rules/ci-registry.md` (required secrets) + `.claude/rules/repos.md` (the repo↔board map).
Reference implementation to copy from: **`ktayl-policy-service`** (all files present). This skill is the
ordered checklist + the traps; companion skills: `wrapper-chart-onboarding` (deploy), `generate-schema-erd`
(if it owns a DB), `wire-llmops` (if it calls an LLM).

## Decide first
- **Public or private?** Org Actions secrets (`GITOPS_TOKEN`, `HARBOR_*`, …) reach **PUBLIC repos only** —
  a private product-home repo's BMAD-sync/CI silently no-ops (empty `GH_TOKEN`). Make product-home repos
  **public** (the intended end state) unless there's a real reason not to. See [[feedback_org_secrets_need_public_repo]].
- **Which product board** does it belong to (`repos.md` / `github-projects.md`)? A repo is a *member* of a
  product, not its own board by default.

## Checklist (before S001 merges to main)
1. **GitHub About** — `gh api repos/andrelair-platform/<repo> --method PATCH -f description="<one line, mentions stack, no trailing period>" -f homepage="https://andrelair-platform.github.io/<repo>/"`
2. **Topics** — `gh api repos/andrelair-platform/<repo>/topics --method PUT -f 'names[]=<lang>' -f 'names[]=kubernetes' -f 'names[]=microservice'` (+ domain tags: `insurance`, `argocd`, …).
3. **`README.md`** — the full mandatory structure (copy from `ktayl-policy-service`): badges (CI · MIT · lang · cosign), `>` one-paragraph description, TOC, Domain/Data model (if DB), Architecture (ASCII CI→ArgoCD→Pod + component table), Getting Started, CI/CD, Endpoints, Env vars, Migrations, Contributing, License.
4. **`LICENSE`** — MIT, correct year (copy + edit).
5. **`CONTRIBUTING.md`** — branch rules + commit style + PR requirements (copy from `ktayl-policy-service`).
6. **release-please** (5 files, copy verbatim from `conventions.md`): `.github/workflows/release.yml`, `release-please-config.json` (set `package-name`; `release-type: node` for Node → no `version.txt`), `.release-please-manifest.json`, `version.txt`, `CHANGELOG.md`.
7. **If it owns a relational schema** → run the `generate-schema-erd` skill (`.tbls.yml` + committed `docs/data-model/` + the `schema-erd-drift` CI job → auto-appears on the central ERD index). **Mandatory for DB repos.**
8. **Central docs pointer** (mandatory) — an overview page in `minicloud-platform-docs/docs/<section>/` + `sidebars.ts` entry linking the repo. (A per-repo `website/` is OPT-IN, flagship only.)
9. **BMAD setup** (before any story code) — `npx bmad-method install --directory . --modules bmm --tools claude-code --yes`; gitignore `_bmad/ _bmad-output/ .claude/`; `/bmad-project-context` → a TINY `AGENTS.md` (policy/command-catches/pitfalls — NOT stack/overview). Then the path-gated planning artefacts (see `bmad-compliance.md`).
10. **Deploy** → the `wrapper-chart-onboarding` skill (GAP chart + Kargo).

## Traps (proven)
- **Private repo + `secrets: inherit` = empty strings** → CI/BMAD-sync/Kargo silently no-op. Public, or add repo-level secret copies.
- **Stale repo-level `HARBOR_USER`/`HARBOR_PASSWORD` shadow the org-level** (repo scope wins) → CI 401 at `docker login`. `gh secret delete` the repo-level ones. Check BOTH `gh secret list --repo` and `--org`.
- **GitHub has NO API to set package visibility** — flip ghcr packages to Internal/Private in the UI after first push (org must allow non-Public packages).
- **Pin CI tool versions** (no `@latest` `go install` / unpinned ruff — it widens defaults silently); let Renovate bump via PR.
- **Container build file is always named `Dockerfile`** (never `Containerfile`).
- **ERD baseline must be generated on x86_64 + pinned pg17.4 + digest-pinned tbls** or you get false drift (see `generate-schema-erd`).
