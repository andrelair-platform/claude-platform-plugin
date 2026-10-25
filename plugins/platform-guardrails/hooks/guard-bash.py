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
  7. a LOCAL `kubectl` with no `--context` — the Mac's default context is `myAKSCluster`,
     so an unqualified kubectl silently targets the wrong cluster (connectivity.md). Fires
     only on a local invocation (a `ssh controller "kubectl …"` has the right context) and
     exempts cluster-agnostic subcommands (config/version/completion/options/help).
  8. `base64 -d` applied to `MINICLOUD_CA_CERT` — it is raw PEM; decoding corrupts the CA
     ("MINICLOUD_CA_CERT is raw PEM — NEVER base64 -d it", connectivity.md / ci-registry.md).
  9. an AI-attribution trailer in a `git commit` / `gh pr|issue` body — `Co-Authored-By` or a
     "Generated with Claude Code" line is forbidden on the owner's portfolio work
     (feedback_no_claude_code_attribution, git-commit-rules).
 10. an in-place `sed -i` on a YAML file — BSD `sed -i ''` corrupts flow-style / Kargo-promoted
     values (gitops.md). Edit YAML with the Edit tool, in block style.
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
# a local kubectl is safe only if it carries --context, or is a cluster-agnostic subcommand.
KUBECTL_CTX_EXEMPT = re.compile(r"(?:^|\s)(?:config|version|completion|options|-h|--help)\b")
# base64 decode in any of its spellings: -d, -D (BSD), --decode.
BASE64_DECODE = re.compile(r"\bbase64\b\s+(?:-{1,2}\w*[dD]\w*|--decode)\b")
# AI-attribution trailers that must never appear on the owner's portfolio work.
ATTRIBUTION = re.compile(
    r"Co-Authored-By|Co-authored-by|Generated with (?:\[)?Claude Code|🤖 Generated with")
GH_AUTHORED = re.compile(r"^gh\s+(?:pr|issue)\s+(?:create|comment|edit)\b")
# an in-place sed (GNU `-i` or BSD `-i ''`) that rewrites a .yaml/.yml file.
SED_INPLACE_YAML = re.compile(r"\bsed\b.*\s-i\b.*\.ya?ml(?:\s|$)")


def check(cmd: str) -> None:
    # whole-command patterns (span a pipe)
    if CURL_PIPE_SH.search(cmd):
        block("Piping a network fetch into a shell is forbidden (supply-chain). "
              "Download, inspect, then run.")
    if "MINICLOUD_CA_CERT" in cmd and BASE64_DECODE.search(cmd):
        block("MINICLOUD_CA_CERT is raw PEM — NEVER `base64 -d` it (connectivity.md). "
              "Use the value verbatim (e.g. write it straight to a .crt).")

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
            if re.match(r"^git\s+commit\b", seg) and ATTRIBUTION.search(seg):
                block("No AI-attribution trailer on commits — remove the `Co-Authored-By` / "
                      "'Generated with Claude Code' line (feedback_no_claude_code_attribution). "
                      "Commits represent the owner's portfolio work.")
        if first == "gh" and GH_AUTHORED.search(seg) and ATTRIBUTION.search(seg):
            block("No AI-attribution line in a PR/issue body — remove the `Co-Authored-By` / "
                  "'Generated with Claude Code' text (feedback_no_claude_code_attribution).")
        if first == "sed" and SED_INPLACE_YAML.search(seg):
            block("Never edit YAML in place with `sed -i` — BSD `sed -i ''` corrupts flow-style / "
                  "Kargo-promoted values (gitops.md). Use the Edit tool, in block style.")
        if first == "kubectl" and "--context" not in seg and not KUBECTL_CTX_EXEMPT.search(seg):
            block("Local kubectl has no --context → it targets the default `myAKSCluster`, not "
                  "the platform (connectivity.md). Add `--context minicloud` (or run it over "
                  "`ssh controller`, whose context is already correct).")
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
