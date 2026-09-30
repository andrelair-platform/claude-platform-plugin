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
| **Hooks** | 2 (Pre/Post) | `guard-bash`, `guard-write`, `validate-yaml` |
| **Skills** | 3 | `secure-api-review`, `wrapper-chart-onboarding`, `prod-promotion-qa-gate` |
| **Commands** | 2 | `/review-pr`, `/capture-intent` |
| **Subagents** | 2 | `verifier`, `researcher` |

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

- **Hooks (deterministic, fail-open):** refuse `rm -rf` of a root, force-push to `main/master`,
  manual `argocd app sync/rollback/patch/set`, `kubectl delete namespace`, `curl|sh`, and
  `git add CLAUDE.md`; refuse writing secret material / vendored `helm/charts/` / an in-repo
  `CLAUDE.md`; run an advisory plain-YAML syntax check after edits. First-token dispatch → near
  zero false positives; a hook bug can never wedge the agent.
- **Skills (triggered):** `secure-api-review` (endpoints/APIs), `wrapper-chart-onboarding`
  (a new service / helm chart), `prod-promotion-qa-gate` (before a prod PR).
- **Commands:** `/review-pr [PR#]` (on-plan severity-tagged review vs the platform policy),
  `/capture-intent "<idea>"` (draft a committed `intent/<slug>.md`).
- **Subagents:** `verifier` (runs the change + evals/curl, report-only), `researcher`
  (read-only fan-out over rules+code, returns the conclusion).

## Managing

```bash
claude plugin update platform-guardrails      # pull the latest (restart to apply)
claude plugin disable platform-guardrails     # temporarily off
claude plugin uninstall platform-guardrails   # remove
```

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
