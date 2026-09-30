#!/usr/bin/env python3
"""PostToolUse advisory check for Write/Edit/MultiEdit — fast YAML syntax feedback.

The edit has already happened; this just tells the agent to fix a broken plain-YAML
file before moving on (exit 2 feeds the message back to Claude). It is ADVISORY and
deliberately conservative:

  * Only *.yaml / *.yml.
  * SKIPS Helm/Kargo templates: any path under a `templates/` dir, or any file whose
    content contains Go-template / Kargo expression markers (`{{` or `${{`) — those are
    not valid standalone YAML and must not be flagged.
  * FAIL-OPEN: if PyYAML isn't importable or anything is unexpected → exit 0.
"""
import json
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
        path = ((data.get("tool_input") or {}).get("file_path") or "")
    except Exception:
        sys.exit(0)

    if not (path.endswith(".yaml") or path.endswith(".yml")):
        sys.exit(0)
    if "/templates/" in path:
        sys.exit(0)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except Exception:
        sys.exit(0)  # file gone/unreadable — not our problem to flag

    if "{{" in content or "${{" in content:
        sys.exit(0)  # Helm / Kargo templating → skip

    try:
        import yaml  # PyYAML; optional
    except Exception:
        sys.exit(0)  # not available → advisory check is a no-op

    try:
        list(yaml.safe_load_all(content))
    except Exception as exc:  # yaml.YAMLError and friends
        sys.stderr.write(
            f"YAML syntax error in {path} after edit:\n{exc}\n"
            "Fix the syntax before continuing.\n"
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
