#!/usr/bin/env python3
"""Git guard (PreToolUse on Bash): the team's git rules, enforced.

Deny:
- `git push --force` / `-f` / `+refspec` without --force-with-lease (rebase is the default; preferences.md).
- `gh pr update-branch`: it pushes to the author's branch and dismisses approvals.

A pack can add its own git rules in a hook of its own.

Ask:
- `git merge main` / `origin/main` and `git pull` without --rebase/--ff-only: rebase is the
  default; a merge is the fallback the developer agrees to, with a reason.

Never breaks a session: any error means it allows the call silently.
"""
import json
import os
import re
import sys

GIT = r"^git(?:\s+(?:-C|-c)\s+\S+|\s+--[\w-]+(?:=\S+)?)*\s+"
PUSH = re.compile(GIT + r"push\b(.*)$")
MERGE_MAIN = re.compile(GIT + r"merge\b(?!.*--(abort|continue|quit)).*\s(origin/)?(main|master)\b")
PULL = re.compile(GIT + r"pull\b(.*)$")


def segments(command):
    for part in re.split(r"&&|\|\||;|\||\n", command):
        part = part.strip().lstrip("(").strip()
        part = re.sub(r"^(\w+=\S*\s+)+", "", part)
        if part:
            yield part


def decide(command, cwd):
    for seg in segments(command):
        push = PUSH.match(seg)
        if push:
            args = push.group(1)
            forced = re.search(r"(^|\s)(--force(?![-\w])|-f\b|-\w*f\w*\b)", args) or re.search(r"\s\+\S", args)
            if forced and "--force-with-lease" not in args:
                return "deny", "Use --force-with-lease, never a plain force push."
        if re.match(r"^gh\s+pr\s+update-branch\b", seg):
            return "deny", "gh pr update-branch pushes to the author's branch and dismisses approvals. Flag the conflict to the author instead."
        if MERGE_MAIN.match(seg):
            return "ask", "Rebase onto origin/main is the default. Approve a merge only if a rebase isn't practical."
        pull = PULL.match(seg)
        if pull and not re.search(r"--rebase\b|-r\b|--ff-only\b", pull.group(1)):
            return "ask", "git pull without --rebase or --ff-only can create a merge commit. Approve, or use --rebase."
    return None


def main():
    data = json.load(sys.stdin)
    command = (data.get("tool_input") or {}).get("command", "")
    result = decide(command, data.get("cwd") or os.getcwd())
    if not result:
        return
    decision, reason = result
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": f"git-guard: {reason}",
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
