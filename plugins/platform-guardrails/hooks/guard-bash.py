#!/usr/bin/env python3
"""PreToolUse guard for Bash — the deterministic layer behind advisory rules.

Blocks (exit 2) a small, high-value set of unambiguously-dangerous or
policy-forbidden commands, and stays out of the way otherwise (exit 0).

Design principles:
  * FAIL-OPEN. Any parse error / unexpected shape → exit 0 (never wedge the agent).
  * FIRST-TOKEN dispatch per shell segment, so `grep "argocd app sync"` or an echo
    that merely *mentions* a dangerous command is NOT blocked — only the real
    invocation is.
  * NARROW patterns → near-zero false positives on normal platform work
    (git add/commit/push feature branches, ssh read-only kubectl, rm of build dirs).

What it blocks + why (each maps to an existing rule):
  1. `rm -rf` of a catastrophic root (/, /*, ~, $HOME, .., .) — irreversible.
  2. force-push to main/master — trunk is protected (git-commit-rules / branch strategy).
  3. manual ArgoCD mutation (`argocd app sync|rollback|patch|set`) — prod moves via a
     CODEOWNERS PR → Kargo, never a manual sync (gitops.md, feedback_never_manual_argocd_sync).
     A human may still run the documented wedge-exception directly, outside the agent.
  4. `kubectl delete namespace|ns` — dropping a namespace is catastrophic.
  5. piping a network fetch straight into a shell (`curl … | sh`) — supply-chain.
  6. `git add … CLAUDE.md` — CLAUDE.md must NEVER be committed (feedback_claude_md_repo_rule).
"""
import json
import os
import re
import sys

# When run as the `platform-guardrails` plugin, Claude Code sets CLAUDE_PLUGIN_ROOT → name the
# plugin in the block message; otherwise this is the repo's committed .claude/hooks/ copy.
_SOURCE = ("plugin: platform-guardrails (guard-bash.py)"
           if os.environ.get("CLAUDE_PLUGIN_ROOT") else ".claude/hooks/guard-bash.py")


def block(msg: str) -> None:
    sys.stderr.write(f"BLOCKED by {_SOURCE}\n" + msg + "\n")
    sys.exit(2)


def segments(command: str):
    """Split a compound command into segments and yield (first_token, segment)."""
    parts = re.split(r"(?:&&|\|\||[;\n|])", command)
    for seg in parts:
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"([\w./-]+)", seg)
        first = m.group(1).split("/")[-1] if m else ""
        yield first, seg


# require an -r/-f flag, then a *standalone* catastrophic target (root, home, cwd, parent).
# A trailing (\s|$) is mandatory so `rm -rf ./build`, `rm -rf /tmp/x`, `rm -rf ~/.cache` all PASS.
DANGEROUS_RM_TARGET = re.compile(
    r"\brm\b(?=.*\s-\w*[rf]\w*\b).*\s(/\*|/|~/|~|\$HOME|\.\.|\.)(\s|$)")
FORCE = re.compile(r"(?:^|\s)(?:-f|--force)(?:\s|$)")
MAINISH = re.compile(r"\b(main|master)\b")
ARGOCD_MUT = re.compile(r"^argocd\s+app\s+(sync|rollback|patch|set)\b")
KUBECTL_NS_DEL = re.compile(r"^kubectl\b.*\bdelete\b.*\b(namespace|ns)\b")
CURL_PIPE_SH = re.compile(r"\b(?:curl|wget)\b[^|]*\|\s*(?:sudo\s+)?(?:bash|sh|zsh)\b")
GIT_ADD_CLAUDEMD = re.compile(r"^git\s+add\b.*\bCLAUDE\.md\b")


def check(cmd: str) -> None:
    # whole-command pattern (spans a pipe)
    if CURL_PIPE_SH.search(cmd):
        block("Piping a network fetch into a shell is forbidden (supply-chain). "
              "Download, inspect, then run.")

    for first, seg in segments(cmd):
        if first == "rm" and DANGEROUS_RM_TARGET.search(seg):
            block("`rm -rf` of a root/home/parent path is irreversible and refused. "
                  "Delete a specific subpath instead.")
        if first == "git":
            if re.match(r"^git\s+push\b", seg) and FORCE.search(seg) and MAINISH.search(seg):
                block("Force-pushing to main/master is refused — trunk is protected "
                      "(branch strategy). Open a PR from a feature branch.")
            if GIT_ADD_CLAUDEMD.search(seg):
                block("CLAUDE.md must NEVER be committed to a repo "
                      "(feedback_claude_md_repo_rule). Do not stage it.")
        if first == "argocd" and ARGOCD_MUT.search(seg):
            block("Manual ArgoCD mutation is refused. Prod moves via a CODEOWNERS PR that "
                  "Kargo opens → ArgoCD auto-syncs (gitops.md). If this is the documented "
                  "wedge-exception, the human operator runs it directly, outside the agent.")
        if first == "kubectl" and KUBECTL_NS_DEL.search(seg):
            block("`kubectl delete namespace` is refused (catastrophic). Namespaces are "
                  "GitOps-managed; remove via the manifest + PR.")
        if first == "ssh":
            # evaluate the remote command inside the first quoted string
            q = re.search(r'"([^"]*)"|\'([^\']*)\'', seg)
            if q:
                inner = q.group(1) or q.group(2) or ""
                for ifirst, iseg in segments(inner):
                    if ifirst == "argocd" and ARGOCD_MUT.search(iseg):
                        block("Manual ArgoCD mutation over ssh is refused (see gitops.md).")
                    if ifirst == "kubectl" and KUBECTL_NS_DEL.search(iseg):
                        block("`kubectl delete namespace` over ssh is refused (catastrophic).")
                    if ifirst == "rm" and DANGEROUS_RM_TARGET.search(iseg):
                        block("`rm -rf` of a root/home path over ssh is refused.")


def main() -> None:
    try:
        data = json.load(sys.stdin)
        cmd = (data.get("tool_input") or {}).get("command", "")
    except Exception:
        sys.exit(0)  # fail-open: a hook bug must never wedge the agent
    if not isinstance(cmd, str) or not cmd.strip():
        sys.exit(0)
    try:
        check(cmd)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
