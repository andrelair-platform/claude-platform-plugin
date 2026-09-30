#!/usr/bin/env python3
"""PreToolUse guard for Write/Edit/MultiEdit — keeps secrets and forbidden files
out of the tree deterministically.

FAIL-OPEN on any parse error (exit 0). Blocks (exit 2) when the incoming content
carries literal secret material, or the target path is one that must never be
hand-edited / committed.

What it blocks + why:
  1. Literal secret material in the new content — private keys, AWS access keys,
     Vault tokens (hvs./hvb.), GitHub PATs, Slack tokens. Secrets belong in Vault
     → ESO, never in a committed file (gitops.md ESO pattern).
  2. Editing a vendored Helm dep under `services/*/helm/charts/` — it is gitignored
     and rebuilt by `helm dependency build`; hand-edits are lost/harmful (gitops.md).
  3. Writing anything under `.git/`.
  4. Creating a `CLAUDE.md` inside this repo — it must NEVER be committed
     (feedback_claude_md_repo_rule). (Hooks are project-scoped, so the workspace-root
     CLAUDE.md outside this repo is unaffected.)
"""
import json
import re
import sys

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"), "a PRIVATE KEY"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "an AWS access key id"),
    (re.compile(r"\bhv[sb]\.[A-Za-z0-9_-]{20,}"), "a Vault token"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "a GitHub personal access token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}"), "a GitHub fine-grained PAT"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "a Slack token"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"), "a GitLab PAT"),
]

PATH_CHARTS = re.compile(r"/helm/charts/")
PATH_GIT = re.compile(r"(^|/)\.git/")


def block(msg: str) -> None:
    sys.stderr.write("BLOCKED by .claude/hooks/guard-write.py\n" + msg + "\n")
    sys.exit(2)


def incoming_text(tool_input: dict) -> str:
    chunks = []
    if isinstance(tool_input.get("content"), str):
        chunks.append(tool_input["content"])           # Write
    if isinstance(tool_input.get("new_string"), str):
        chunks.append(tool_input["new_string"])         # Edit
    for e in tool_input.get("edits", []) or []:          # MultiEdit
        if isinstance(e, dict) and isinstance(e.get("new_string"), str):
            chunks.append(e["new_string"])
    return "\n".join(chunks)


def main() -> None:
    try:
        data = json.load(sys.stdin)
        ti = data.get("tool_input") or {}
        path = ti.get("file_path", "") or ""
    except Exception:
        sys.exit(0)
    try:
        if PATH_GIT.search(path):
            block("Refusing to write under .git/.")
        if PATH_CHARTS.search(path):
            block("services/*/helm/charts/ is a vendored, gitignored Helm dependency "
                  "rebuilt by `helm dependency build` — do not hand-edit it (gitops.md).")
        if path.rstrip("/").split("/")[-1] == "CLAUDE.md":
            block("CLAUDE.md must NEVER live in a committed repo "
                  "(feedback_claude_md_repo_rule). Put durable context in "
                  ".claude/rules/*.md, AGENTS.md, or the memory system instead.")
        text = incoming_text(ti)
        for pat, label in SECRET_PATTERNS:
            if pat.search(text):
                block(f"Refusing to write {label} into a file. Secrets go to Vault "
                      f"→ ESO (ExternalSecret), never committed content (gitops.md).")
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
