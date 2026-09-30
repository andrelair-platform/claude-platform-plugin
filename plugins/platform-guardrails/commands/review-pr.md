---
description: Review a PR (or the current branch diff) against REVIEW.md — local, on-plan, no CI/API cost.
argument-hint: "[PR number | branch name | blank = current branch vs main]"
allowed-tools: Bash(gh pr diff:*), Bash(gh pr view:*), Bash(git diff:*), Bash(git log:*), Bash(git merge-base:*), Read, Grep, Glob
---

You are running the platform's **PR review** (Anthropic AI-native SDLC Play 10), locally
on the owner's Claude Code plan. Follow `@REVIEW.md` as the policy of record.

## Target
`$ARGUMENTS`
- If it's a number → `gh pr diff $ARGUMENTS` for the diff and `gh pr view $ARGUMENTS` for the body.
- If it's a branch name → `git diff main...$ARGUMENTS`.
- If blank → `git diff main...HEAD` (current branch vs its merge-base with main).

## Steps
1. Load the diff (and the PR body, if a PR number was given).
2. Read `@REVIEW.md`. For any changed area that maps to a gated/sensitive path, also read
   the relevant `.claude/rules/*.md` and the matching `.claude/skills/*/SKILL.md`
   (e.g. an endpoint → `secure-api-review`; a helm chart → `wrapper-chart-onboarding`; a
   prod/Kargo change → `prod-promotion-qa-gate`).
3. If the PR body or the branch links a `plan.md`/`spec.md`/issue, check the diff against
   the **stated intent** — does it do what was planned, no more, no less?
4. Run the three passes (**Bugs / Security / Compliance-with-intent**) plus the platform
   must-checks in `REVIEW.md`.
5. Emit the output in `REVIEW.md`'s format: a one-line verdict (`SHIP` / `FIX-FIRST`),
   then findings grouped **🔴 Important** then **🟡 Nit**, each tagged
   `[Bugs|Security|Compliance]` with `file:line` and the fix. Cap nits at 5 (+ a count).

## Hard rules
- **Do NOT merge, approve, push, or edit anything.** This is a read-only review that
  informs the human CODEOWNERS gate. Report only.
- Do not re-report what CI already enforces (checkov/kubeconform/Trivy/cosign) or issues
  outside the diff.
- If the change crosses a security/architecture boundary, say so explicitly (it needs the
  governance gate, not just CODEOWNERS).
