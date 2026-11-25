#!/usr/bin/env python3
"""PreToolUse guard for Bash: block patterns zsh expands that bash would not.

zsh treats a word starting with '=' as a command lookup (`echo =====` fails with
"= not found") and expands an unquoted glob such as `--include=*.ts` itself,
failing with "no matches found". Quoted text and heredoc bodies are ignored.
Does nothing unless $SHELL is zsh, since Claude Code runs Bash commands in the user's shell.
"""
import json
import os
import re
import sys

if os.path.basename(os.environ.get("SHELL", "")) != "zsh":
    sys.exit(0)

command = json.load(sys.stdin).get("tool_input", {}).get("command", "")


def strip_heredocs(text: str) -> str:
    lines = text.split("\n")
    out, terminator = [], None
    for line in lines:
        if terminator is not None:
            if line.strip() == terminator:
                terminator = None
            continue
        out.append(line)
        match = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
        if match:
            terminator = match.group(1)
    return "\n".join(out)


unquoted = strip_heredocs(command)
unquoted = re.sub(r"'[^']*'", "''", unquoted)
unquoted = re.sub(r'"(?:\\.|[^"\\])*"', '""', unquoted)

problems = []
if re.search(r"(^|[\s;|&(])=[^\s]", unquoted):
    problems.append("a word starting with '=' (zsh runs it as a command lookup), e.g. echo '-----' instead of echo =====")
if re.search(r"--\w[\w-]*=[^\s'\"]*[*?\[]", unquoted):
    problems.append("an unquoted glob in a --flag=value argument, e.g. '--include=*.ts'")

if problems:
    print("The shell is zsh. Quote " + "; or ".join(problems) + ".", file=sys.stderr)
    sys.exit(2)

# zsh doesn't split an unquoted $VAR, so P="--profile x --region y" then `aws ... $P` passes one
# argument and every call fails.
if re.search(r"(^|[\s;&|(])(?:export\s+|local\s+)?[A-Za-z_]\w*=([\"'])-[^\"'\n]*\s-[^\"'\n]*\2", strip_heredocs(command)):
    print(
        "The shell is zsh, which won't split a variable holding several flags. "
        "Write the flags out, or use AWS_PROFILE/AWS_REGION env vars.",
        file=sys.stderr,
    )
    sys.exit(2)
