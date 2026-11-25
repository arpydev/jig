#!/usr/bin/env python3
"""Docs guard (PreToolUse on Write and Edit): keep the glossary and ADRs where the project put them.

Each project's settings (.claude/workflow.json, in the main checkout) name where its glossary
and ADRs live (`docs.glossary`, `docs.adr`). Some projects keep them outside the repository.
For those, creating a new GLOSSARY.md or ADR file inside the repository is denied, with the
place it belongs. Projects that keep them in the repository, and repositories without
settings, are never touched. The toggle is the paths in the settings.

Never breaks a session: any error means it allows the call silently.
"""
import json
import os
import re
import subprocess
import sys

SETTINGS = os.path.join(".claude", "workflow.json")


def existing_folder(path):
    folder = os.path.dirname(path)
    while folder and not os.path.isdir(folder):
        folder = os.path.dirname(folder)
    return folder


def main_checkout(folder):
    out = subprocess.run(["git", "-C", folder, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return os.path.dirname(os.path.realpath(out.stdout.strip()))


def inside(path, folder):
    return path == folder or path.startswith(folder + os.sep)


def decide(path):
    """Return a reason to deny writing the file at path, or None."""
    name = os.path.basename(path)
    kind = None
    if name == "GLOSSARY.md":
        kind = "glossary"
    elif re.search(r"/(adr|adrs|decisions)/", path, re.I) or re.match(r"ADR[-_]?\d+", name, re.I):
        kind = "adr"
    if not kind or os.path.exists(path):
        return None
    root = main_checkout(existing_folder(path))
    if not root:
        return None
    settings_path = os.path.join(root, SETTINGS)
    if not os.path.exists(settings_path):
        return None
    with open(settings_path) as f:
        target = (json.load(f).get("docs") or {}).get(kind)
    if not target:
        return None
    target = os.path.realpath(os.path.join(root, os.path.expanduser(target)))
    if inside(target, root) or inside(path, target):
        return None
    label = "glossary" if kind == "glossary" else "ADRs"
    return f"This project keeps its {label} outside the repository, at {target}. Write it there instead."


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") not in ("Write", "Edit"):
        return
    raw = (data.get("tool_input") or {}).get("file_path", "")
    reason = decide(os.path.realpath(os.path.expanduser(raw)))
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"docs-guard: {reason}",
        }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
