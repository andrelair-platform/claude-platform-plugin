# claude-platform-plugin — `andrelair-platform` marketplace

Single-source distribution of the platform's **AI-native SDLC** agent config (Anthropic
12-play playbook). Install it **once** and the guardrails + skills + commands + subagents
apply in **every** repo you open — no per-repo copies to drift, central updates.

## Plugin: `platform-guardrails`

| Component | What |
|---|---|
| **Hooks** (`hooks/`) | deterministic guards, fail-open: refuse `rm -rf` of a root, force-push to main, manual `argocd app sync`, `kubectl delete namespace`, `curl\|sh`, `git add CLAUDE.md`; refuse writing secret material / vendored `helm/charts/` / in-repo `CLAUDE.md`; advisory plain-YAML syntax check |
| **Skills** (`skills/`) | `secure-api-review`, `wrapper-chart-onboarding`, `prod-promotion-qa-gate` (triggered) |
| **Commands** (`commands/`) | `/review-pr`, `/capture-intent` |
| **Agents** (`agents/`) | `verifier`, `researcher` |

Source of truth for the reference copies + the deterministic eval suite:
`minicloud-gitops/.claude/` (+ `evals/`). This marketplace is the distribution layer; the
skills' `.claude/rules/*.md` pointers refer to that repo's constitution.

## Install (once, on your machine)

```bash
claude plugin marketplace add andrelair-platform/claude-platform-plugin
claude plugin install platform-guardrails@andrelair-platform
# restart the session; verify:
claude plugin list
```

Because it's installed at the user level, it applies across **all** repos automatically.
Update everywhere with `claude plugin update platform-guardrails`.

## Note on overlap with `minicloud-gitops`

`minicloud-gitops` keeps its **own committed** `.claude/{settings.json,hooks,skills,…}`
(versioned + CODEOWNERS-gated + regression-tested by `evals/`). When you work there, both
the committed hooks and the plugin hooks match — a harmless double-run (same verdict). The
committed copy is the reviewed reference; this plugin is how every *other* repo gets them.
