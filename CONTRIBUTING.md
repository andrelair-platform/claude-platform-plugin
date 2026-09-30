# Contributing

## Source of truth
The canonical copies of the hooks/skills/commands/agents live in
**`minicloud-gitops/.claude/`** (committed, CODEOWNERS-gated, regression-tested by that repo's
`evals/`). Change them **there first**; this repo is the distribution layer. Keep the two in
sync — the reference eval (`evals/test_hooks.py`) is the behaviour contract for the hooks.

## Workflow
- Branch: `feat/…`, `fix/…`, `docs/…` → PR → `main`. No direct pushes to `main`.
- **Commits are GPG-signed** (`git config commit.gpgsign true`), identity `AndreLiar`.
- The **`validate` workflow must pass**: the marketplace + plugin manifests validate and every
  hook script compiles. Run locally before pushing:
  ```bash
  claude plugin validate .                                   # marketplace
  claude plugin validate plugins/platform-guardrails         # plugin
  python3 -m py_compile plugins/platform-guardrails/hooks/*.py
  ```
- On any **behaviour change**, bump `plugins/platform-guardrails/.claude-plugin/plugin.json`
  `version` so `claude plugin update` picks it up. Optionally tag a release with
  `claude plugin tag`.

## Hooks discipline
Hooks must **fail-open** (a parse error → exit 0, never wedge the agent) and use narrow,
first-token dispatch to avoid false positives. Any new block rule needs an allow-case **and** a
block-case added to the reference matrix in `minicloud-gitops/evals/test_hooks.py`.

## No secrets
Never commit tokens/keys. The `guard-write` hook itself refuses secret material — don't work
around it.
