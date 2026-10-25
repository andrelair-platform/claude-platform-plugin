# claude-platform-plugin

[![Validate](https://github.com/andrelair-platform/claude-platform-plugin/actions/workflows/validate.yml/badge.svg)](https://github.com/andrelair-platform/claude-platform-plugin/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-blueviolet)](https://docs.claude.com/en/docs/claude-code/plugins)
[![AI-native SDLC](https://img.shields.io/badge/AI--native%20SDLC-12--play-green)](https://andrelair-platform.github.io/minicloud-platform-docs/)

> Single-source distribution of the **ktayl/minicloud** platform's AI-native SDLC agent
> config (Anthropic 12-play playbook). Install it **once** and the deterministic guardrails,
> policy skills, commands and subagents apply in **every** repo you open — no per-repo copies
> to drift, updated centrally.

**Marketplace:** `andrelair-platform` · **Plugin:** `platform-guardrails`
**Platform docs:** <https://andrelair-platform.github.io/minicloud-platform-docs/>

---

## Table of Contents
- [What's in it](#whats-in-it)
- [Install](#install)
- [Components](#components)
- [Managing](#managing)
- [Architecture — how it's distributed](#architecture--how-its-distributed)
- [Relationship to minicloud-gitops](#relationship-to-minicloud-gitops)
- [Contributing](#contributing)
- [License](#license)

## What's in it

| Component | Count | Names |
|---|---|---|
| **Hooks** | 3 (Pre/Pre/Post) | `guard-bash` (10 rules), `guard-write` (6 rules), `validate-yaml` (advisory) |
| **Skills** | 18 | `secure-api-review`, `wrapper-chart-onboarding`, `prod-promotion-qa-gate`, `standardize-new-repo`, `test-pyramid-setup`, `longhorn-incident-recovery`, `cnpg-migration`, `generate-schema-erd`, `offsite-dr-backup`, `run-game-day`, `wire-llmops`, `github-board-ops`, `public-sso-app-forwardauth`, `make-architecture-diagram`, `wire-vault-secret`, `authentik-app-onboarding`, `cilium-netpol`, `kargo-warehouse-wiring` |
| **Commands** | 2 | `/review-pr`, `/capture-intent` |
| **Subagents** | 2 | `verifier`, `researcher` |
| **Evals** | 1 | `evals/test_hooks.py` (30 cases, both guards) |

## Install

```bash
claude plugin marketplace add andrelair-platform/claude-platform-plugin
claude plugin install platform-guardrails@andrelair-platform
# restart the session, then verify:
claude plugin list
claude plugin details platform-guardrails
```

Installed at **user scope**, so it applies across **all** repos automatically. Plugin
components load at **session start** (active the next session). Re-run the two commands on any
other machine.

## Components

- **Hooks (deterministic, fail-open):** `guard-bash` refuses `rm -rf` of a root, force-push to
  `main/master`, manual `argocd app sync/rollback/patch/set`, `kubectl delete namespace`,
  `curl|sh`, `git add CLAUDE.md`, a **local `kubectl` with no `--context`**, **`base64 -d` of
  `MINICLOUD_CA_CERT`**, an **AI-attribution trailer** in a `git commit`/`gh pr` body, and an
  **in-place `sed -i` on YAML**. `guard-write` refuses secret material, vendored `helm/charts/`,
  an in-repo `CLAUDE.md`, a **`Containerfile`**, and the **real-employer token** in an artefact.
  `validate-yaml` is an advisory post-edit check. First-token dispatch → near-zero false positives;
  a hook bug can never wedge the agent; `evals/test_hooks.py` pins the behaviour (30 cases).
- **Skills (triggered):** 18 policy skills spanning API security, the GAP wrapper-chart golden path,
  prod promotion + Kargo wiring, Longhorn/CNPG/DR recovery, secrets (Vault→ESO), Authentik SSO/M2M,
  Cilium netpols, ERDs, LLMOps, game days, boards and diagrams.
- **Commands:** `/review-pr [PR#]` (on-plan severity-tagged review vs the platform policy),
  `/capture-intent "<idea>"` (draft a committed `intent/<slug>.md`).
- **Subagents:** `verifier` (runs the change + evals/curl, report-only), `researcher`
  (read-only fan-out over rules+code, returns the conclusion).

## Managing

```bash
claude plugin update platform-guardrails      # pull the latest (restart to apply)
claude plugin disable platform-guardrails     # temporarily off
claude plugin uninstall platform-guardrails   # remove
claude plugin prune                           # drop stale cached versions (e.g. an old 1.0.1 dir)
```

## Releasing a plugin change (add/edit a skill, hook, command) — the 4 steps

**The gotcha this prevents:** installed plugins load from a **version-pinned cache**
(`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`). Merging to `main` is **not** enough —
if `plugin.json`'s `version` didn't bump, or the local cache wasn't updated, your sessions keep loading
the **old** skills/hooks. Always:

```bash
# 1. In the PR that adds/edits the skill|hook|command, BUMP the version:
#    plugins/platform-guardrails/.claude-plugin/plugin.json  "version": "1.3.0" -> "1.4.0"
#    (and mirror the artifact into minicloud-gitops/.claude/ — the source of truth, see below)

# 2. After it merges to main, refresh the marketplace from GitHub:
claude plugin marketplace update andrelair-platform

# 3. Update the installed plugin to the new version:
claude plugin update platform-guardrails@andrelair-platform    # --scope user (default)

# 4. RESTART Claude Code — the running session holds the OLD version in memory until you relaunch.
```

Verify after restart: the new skills appear in the session's available-skills list, and
`claude plugin list` shows the bumped version. Project-scoped skills
(`minicloud-gitops/.claude/skills/`) load **live** from the repo clone and need none of this — only the
**plugin** (user-scope, every-project) delivery goes through the cache.

## Architecture — how it's distributed

```
  minicloud-gitops/.claude/  ──(source of truth: committed, CODEOWNERS-gated, eval-tested)
            │  copied into
            ▼
  claude-platform-plugin (this repo = the marketplace)
     .claude-plugin/marketplace.json → plugins/platform-guardrails/
            │  claude plugin install (once, user scope)
            ▼
  every repo session on the machine  ← hooks + skills + commands + agents apply
```

## Relationship to minicloud-gitops

`minicloud-gitops` keeps its **own committed** `.claude/{settings.json,hooks,skills,commands,
agents}` — versioned, CODEOWNERS-gated, and regression-tested by its `evals/` suite. That is
the **source of truth + reviewed reference**; this repo is the **distribution layer** that
carries the same artifacts to every other repo. Working in `minicloud-gitops` runs both its
committed hooks and the plugin's — a harmless double-run (identical verdict).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: branch → PR → the `validate` workflow must
pass (manifests valid + hooks compile) → GPG-signed commits. Bump `plugin.json` `version` on a
behaviour change so `claude plugin update` picks it up.

## License

[MIT](LICENSE) © AndreLiar
