#!/usr/bin/env python3
"""Outbound guard (PreToolUse): writes to Jira, Confluence and GitHub need the developer's yes.

Backs the "confirm before external writes" rule. Every Atlassian write tool, and every Bash
command that posts to GitHub or pushes, returns "ask", so the developer sees a permission prompt
showing the text about to go out. A pack's scripts that post after their own
confirmation are not matched, because the hook sees only the command
that runs the script.

Packs add text checks without changing this file: every outbound-checks/*.py next to this hook
(OUTBOUND_CHECKS_DIR overrides the folder) may define check(text), returning a reason to deny the
write or None, such as a pack's check that denies anything that looks like a real customer identifier,
and warn(text, cwd), returning lines to add to the prompt without blocking, such as the core's
knowledge-map check.

Never breaks a session: any error means it stays silent and the normal permission flow applies.
"""
import glob
import importlib.util
import json
import os
import re
import sys

ATLASSIAN_WRITES = re.compile(
    r"^mcp__.*atlassian.*__("
    r"createJiraIssue|editJiraIssue|addCommentToJiraIssue|addOrEditJiraIssueComment|"
    r"transitionJiraIssue|createIssueLink|executeWrite|executeDestructive|"
    r"createConfluenceContent|updateConfluenceContent|createConfluencePage|updateConfluencePage|"
    r"createConfluenceFooterComment|createConfluenceInlineComment"
    r")$"
)

# Bash commands that publish something. Matched per command segment (split on ; && || |).
BASH_WRITES = [
    (re.compile(r"^git(\s+(-C|-c)\s+\S+|\s+--[\w-]+(=\S+)?)*\s+push\b"), "git push"),
    (re.compile(r"^gh\s+pr\s+(create|comment|review|edit|close|reopen|ready|merge)\b"), "gh pr write"),
    (re.compile(r"^gh\s+issue\s+(create|comment|edit|close|reopen|transfer|delete)\b"), "gh issue write"),
    (re.compile(r"^gh\s+release\s+(create|edit|delete|upload)\b"), "gh release write"),
    (re.compile(r"^gh\s+api\b.*(\s-X\s*|\s--method\s+)(POST|PATCH|PUT|DELETE)\b", re.I), "gh api write"),
    (re.compile(r"^gh\s+api\b.*\s(-f|-F|--field|--raw-field|--input)\s"), "gh api write"),
]

CHECKS_DIR = os.environ.get("OUTBOUND_CHECKS_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "outbound-checks")


def segments(command: str):
    for part in re.split(r"&&|\|\||;|\||\n", command):
        part = part.strip().lstrip("(").strip()
        part = re.sub(r"^(\w+=\S*\s+)+", "", part)  # leading VAR=value assignments
        if part:
            yield part


def decide(tool: str, tool_input: dict, cwd: str = ""):
    """Return (decision, reason) or None."""
    if ATLASSIAN_WRITES.match(tool):
        text = json.dumps(tool_input, ensure_ascii=False)
        return outbound_text_check(text, cwd, f"External write ({tool.split('__')[-1]}). Approve only if this is the wording you agreed.")
    if tool == "Bash":
        command = tool_input.get("command", "")
        for seg in segments(command):
            for pattern, label in BASH_WRITES:
                if pattern.search(seg):
                    return outbound_text_check(command, cwd, f"External write ({label}). Approve only if you asked for this.")
    return None


def checks():
    for path in sorted(glob.glob(os.path.join(CHECKS_DIR, "*.py"))):
        spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3].replace("-", "_"), path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


def outbound_text_check(text: str, cwd: str, ask_reason: str):
    """Deny on the first check's reason; otherwise ask, with every check's warnings added."""
    modules = list(checks())
    for module in modules:
        reason = getattr(module, "check", lambda _: None)(text)
        if reason:
            return ("deny", reason)
    warnings = []
    for module in modules:
        try:
            warnings += getattr(module, "warn", lambda *_: [])(text, cwd) or []
        except Exception:
            pass  # why: a warning is advisory, so a broken one must not stop the prompt
    return ("ask", " ".join([ask_reason, *warnings]))


def main():
    data = json.load(sys.stdin)
    result = decide(data.get("tool_name", ""), data.get("tool_input") or {}, data.get("cwd") or os.getcwd())
    if not result:
        return
    decision, reason = result
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": f"outbound-guard: {reason}",
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
