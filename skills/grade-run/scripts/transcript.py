#!/usr/bin/env python3
"""Render Claude Code transcripts (.jsonl) as plain text for the run grader.

Usage: python3 -I transcript.py <run.jsonl> [<run.jsonl> ...] [USER_LABEL] > transcript.txt

Pass several files, oldest first: the sessions of one developer-driven run (each starts with a
===== SESSION line), or the implementer runs of one ticket worked more than once (a rework, each
starts with a ===== RUN line). They are rendered into one transcript. USER_LABEL names who wrote the plain user
messages: DEVELOPER for a session the developer drove (the default), ORCHESTRATOR for an
implementer subagent, whose prompt came from the orchestrating session.

Keeps the developer's messages, Claude's text, every tool call with its input, and the head and
tail of each tool result (the command's opening and its pass/fail summary), so the grader can
check each claim against the tool output that backs it without reading every line of output.
"""

import json
import sys

RESULT_HEAD = 200
RESULT_TAIL = 200
# Edit and Write bodies are the bulk of tool inputs; the grader reads those changes in the diff.
INPUT_CHARS = 300
FULL_INPUT_TOOLS = {"SubagentHandback"}


def text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "tool_result":
                parts.append(text_of(block.get("content")))
    return "\n".join(parts)


def trimmed(text):
    if len(text) <= RESULT_HEAD + RESULT_TAIL:
        return text
    cut = len(text) - RESULT_HEAD - RESULT_TAIL
    return f"{text[:RESULT_HEAD]}\n[... {cut} characters cut ...]\n{text[-RESULT_TAIL:]}"


def render(path, user_label):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = entry.get("type")
            message = entry.get("message") or {}
            content = message.get("content")
            if kind == "user":
                if isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_result" for b in content
                ):
                    print(f"[TOOL RESULT]\n{trimmed(text_of(content))}\n")
                else:
                    print(f"[{user_label}]\n{text_of(content)}\n")
            elif kind == "assistant" and isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        print(f"[CLAUDE]\n{block['text']}\n")
                    elif block.get("type") == "tool_use":
                        tool_input = json.dumps(block.get("input"), ensure_ascii=False)
                        # A subagent's final report travels as this call; the grader checks it
                        # against the transcript, so it is never cut short.
                        limit = None if block.get("name") in FULL_INPUT_TOOLS else INPUT_CHARS
                        print(f"[TOOL CALL] {block.get('name')}\n{tool_input[:limit]}\n")


def main(args):
    user_label = "DEVELOPER"
    if args and not args[-1].endswith(".jsonl"):
        user_label = args[-1]
        args = args[:-1]
    if not args:
        sys.exit("Usage: transcript.py <run.jsonl> [<run.jsonl> ...] [USER_LABEL]")
    for index, path in enumerate(args, start=1):
        if len(args) > 1:
            # A developer's run spans sessions; an implementer's ticket spans runs (reworks).
            unit = "SESSION" if user_label == "DEVELOPER" else "RUN"
            print(f"===== {unit} {index} of {len(args)}: {path} =====\n")
        render(path, user_label)


if __name__ == "__main__":
    main(sys.argv[1:])
