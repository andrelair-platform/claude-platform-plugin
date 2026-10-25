# Changelog

All notable changes to the **platform-guardrails** plugin are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com); this plugin uses
[Semantic Versioning](https://semver.org). The version is `plugins/platform-guardrails/.claude-plugin/plugin.json`.

## [1.4.0] - 2026-10-25

### Added
- **4 new deterministic Bash guards** (`guard-bash`): refuse a **local `kubectl` with no
  `--context`** (default context is `myAKSCluster`; `ssh controller` is exempt), **`base64 -d` of
  `MINICLOUD_CA_CERT`** (raw PEM), an **AI-attribution trailer** in a `git commit` / `gh pr|issue`
  body (`Co-Authored-By` / "Generated with Claude Code"), and an **in-place `sed -i` on a YAML file**
  (corrupts flow-style / Kargo-promoted values).
- **2 new deterministic Write guards** (`guard-write`): refuse creating a **`Containerfile`** (house
  convention is `Dockerfile`), and writing the **real-employer token** into a platform/ktayl artefact
  (the hdi-missions memory path is exempt).
- **4 new Skills**: `wire-vault-secret` (Vault → ESO → pod, incl. the SSA `ignoreDifferences` gotcha +
  `ghcr-pull`), `authentik-app-onboarding` (native OIDC + M2M client-credentials), `cilium-netpol`
  (the kube-apiserver-identity gotcha + 504 selector-mismatch), `kargo-warehouse-wiring` (image vs git
  model + the NewestBuild monotonic-timestamp trap).
- **`evals/test_hooks.py`** — a deterministic 30-case exit-code harness for both guards
  (the `verifier` subagent's `python3 evals/test_hooks.py`). All 30 green.

## [1.0.1] - 2026-09-30

### Fixed
- **Block-message attribution.** The `guard-bash` / `guard-write` block message now reads
  `plugin: platform-guardrails (<script>.py)` when run as this plugin (Claude Code sets
  `CLAUDE_PLUGIN_ROOT`), and keeps `.claude/hooks/<script>.py` for the committed
  `minicloud-gitops` copy. Exit codes and behaviour unchanged (eval matrix 36/36 green).

## [1.0.0] - 2026-09-30

### Added
- Initial release: the `platform-guardrails` plugin + the `andrelair-platform` marketplace —
  single-source distribution of the AI-native SDLC agent config across every repo.
- **Hooks** (fail-open, first-token dispatch): `guard-bash` (refuse `rm -rf` of a root,
  force-push to `main/master`, manual `argocd app sync/rollback/patch/set`,
  `kubectl delete namespace`, `curl|sh`, `git add CLAUDE.md`), `guard-write` (refuse secret
  material / vendored `helm/charts/` / in-repo `CLAUDE.md`), `validate-yaml` (advisory).
- **Skills**: `secure-api-review`, `wrapper-chart-onboarding`, `prod-promotion-qa-gate`.
- **Commands**: `/review-pr`, `/capture-intent`.
- **Subagents**: `verifier`, `researcher`.
