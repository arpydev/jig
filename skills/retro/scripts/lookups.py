#!/usr/bin/env python3
"""List the exploration a run did, so the retro can count repeated lookups and turn them into scripts.

Usage:
  python3 -I lookups.py <session.jsonl> [<session.jsonl> ...]                # one run, oldest first
  python3 -I lookups.py --scripts-only <session.jsonl> [<session.jsonl> ...]  # script runs only

Prints the run's totals, how many times each workflow script ran, then one line per exploration
call: its number, tool, result size and a one-line summary of its input. A "---" line marks
each developer message, so the calls can be grouped by the question they were answering.
Result contents are never printed, only their sizes.

An exploration call is a Grep, Glob, Read, WebFetch, WebSearch or Agent call, a read-type MCP
call (get, search, list, read, fetch, lookup, query or view in its name), or a Bash command
whose first program reads rather than changes (grep, find, cat, git log, gh pr view and the
like). A Bash command that runs a workflow script counts as a script run, not as exploration.
Reads of a skill's own files (under ~/.claude/skills, the core or an installed pack) are the
skill working as designed, so they're counted on the totals line but not listed.
Workflow scripts are the files in <skills>/*/scripts/ of the core (next to this file), the
installed skills and every pack in <claude home>/workflow-packs.
Subagents' own tool calls live in separate transcripts and aren't counted here; the Agent call
that started them is, with the size of its report.
"""

import json
import os
import re
import shlex
import sys
from collections import Counter

INPUT_CHARS = 160
DEVELOPER_CHARS = 80
SEARCH_TOOLS = {"Grep", "Glob", "Read", "WebFetch", "WebSearch", "Agent"}
READ_MCP = re.compile(r"(get|search|list|read|fetch|lookup|query|view)", re.IGNORECASE)
READ_PROGRAMS = {
    "grep", "rg", "find", "ls", "cat", "head", "tail", "less", "wc", "tree", "jq", "file", "stat",
    "diff", "awk", "realpath", "readlink", "which", "du",
}
READ_SUBCOMMANDS = {
    "git": {"log", "show", "diff", "grep", "blame", "ls-files", "ls-tree", "branch", "status",
            "rev-parse", "describe", "tag", "remote", "cat-file", "for-each-ref", "shortlog"},
    "gh": {"pr", "issue", "api", "search", "run", "repo", "release", "workflow"},
}
WRITE_WHEN_REDIRECTED = {"cat", "tee"}
SKILL_PATHS = ("/.claude/skills/",)  # a skill reading its own files isn't a lookup; skill_roots() adds the rest
GH_WRITE = {"create", "merge", "close", "edit", "comment", "review", "reopen", "delete", "rerun"}
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\|")


def skill_roots():
    home = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    roots = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), os.path.join(home, "skills")]
    packs = os.path.join(home, "workflow-packs")
    if os.path.exists(packs):
        with open(packs) as fh:
            roots += [os.path.join(line.strip(), "skills") for line in fh if line.strip()]
    return roots


def skills_root():
    return skill_roots()[0]


def workflow_scripts(roots):
    if isinstance(roots, str):
        roots = [roots]
    names = set()
    for root in roots:
        names |= _scripts_in(root)
    return names


def _scripts_in(root):
    names = set()
    for skill in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        folder = os.path.join(root, skill, "scripts")
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and not name.startswith(("test_", ".")):
                names.add(name)
    return names


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


def one_line(text, limit):
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def tokens(segment):
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


RUNNERS = {"python", "python3", "bash", "sh", "zsh", "env", "uv", "uvx"}


def program_of(words):
    """The program a command segment runs: skips VAR=value, and interpreters and their flags."""
    words = list(words)
    while words and "=" in words[0] and not words[0].startswith("-"):
        words.pop(0)
    while words and (os.path.basename(words[0]) in RUNNERS or words[0].startswith("-")):
        words.pop(0)
    return os.path.basename(words[0]) if words else None


def scripts_in(command, scripts):
    found = []
    for segment in SEGMENT_SPLIT.split(command):
        name = program_of(tokens(segment.strip()))
        if name in scripts:
            found.append(name)
    return found


def is_read_segment(words):
    while words and "=" in words[0] and not words[0].startswith("-"):
        words = words[1:]  # leading VAR=value
    if not words:
        return None
    program = os.path.basename(words[0])
    if program == "cd":
        return None
    if program in WRITE_WHEN_REDIRECTED and any(w.startswith(">") for w in words):
        return False  # cat > file <<EOF writes a file
    if program in READ_PROGRAMS:
        return True
    if program == "sed":
        return "-n" in words
    if program == "aws":
        return len(words) > 2 and words[2].startswith(("describe", "get", "list"))
    if program == "gh":
        if len(words) < 2 or words[1] not in READ_SUBCOMMANDS["gh"]:
            return False
        return not (set(words[2:3]) & GH_WRITE) and "-X" not in words and "--method" not in words
    if program == "git":
        rest = words[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
        return bool(rest) and rest[0] in READ_SUBCOMMANDS["git"]
    return False


def is_read_bash(command):
    for segment in SEGMENT_SPLIT.split(command):
        verdict = is_read_segment(tokens(segment.strip()))
        if verdict is not None:
            return verdict  # the first real program decides
    return False


def summarise(name, tool_input):
    tool_input = tool_input or {}
    if name == "Bash":
        return tool_input.get("command", "")
    if name == "Read":
        extra = f" @{tool_input['offset']}" if tool_input.get("offset") else ""
        return f"{tool_input.get('file_path', '')}{extra}"
    if name == "Grep":
        where = tool_input.get("path") or tool_input.get("glob") or ""
        return f"{tool_input.get('pattern', '')!r} {where}".strip()
    if name == "Glob":
        return f"{tool_input.get('pattern', '')} {tool_input.get('path', '')}".strip()
    if name == "Agent":
        return f"[{tool_input.get('subagent_type', 'general-purpose')}] {tool_input.get('description', '')}"
    if name in ("WebFetch", "WebSearch"):
        return tool_input.get("url") or tool_input.get("query", "")
    return json.dumps(tool_input, ensure_ascii=False)


def is_exploration(name, tool_input):
    if name in SEARCH_TOOLS:
        return True
    if name == "Bash":
        return is_read_bash((tool_input or {}).get("command", ""))
    if name.startswith("mcp__"):
        return bool(READ_MCP.search(name.rsplit("__", 1)[-1]))
    return False


def short_name(name):
    """mcp__plugin_atlassian_atlassian__getJiraIssue -> mcp:getJiraIssue"""
    return f"mcp:{name.rsplit('__', 1)[-1]}"[:24] if name.startswith("mcp__") else name[:24]


def size(chars):
    return f"{chars / 1000:.1f}k" if chars >= 1000 else str(chars)


def scan(paths):
    events, calls, results = [], {}, {}
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = (entry.get("message") or {}).get("content")
                if entry.get("type") == "user":
                    blocks = content if isinstance(content, list) else []
                    tool_results = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_result"]
                    for block in tool_results:
                        results[block.get("tool_use_id")] = len(text_of(block.get("content")))
                    if not tool_results and not entry.get("isMeta"):
                        events.append(("developer", one_line(text_of(content), DEVELOPER_CHARS)))
                elif entry.get("type") == "assistant" and isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            calls[block.get("id")] = (block.get("name", ""), block.get("input"))
                            events.append(("call", block.get("id")))
    return events, calls, results


def report(paths, scripts_only=False, scripts=None):
    scripts = workflow_scripts(skill_roots()) if scripts is None else scripts
    own_files = SKILL_PATHS + tuple(os.path.realpath(r) + "/" for r in skill_roots())
    events, calls, results = scan(paths)
    script_runs = Counter()
    lines, explored, explored_chars, number, skill_reads = [], 0, 0, 0, 0
    pending_developer = None
    for kind, value in events:
        if kind == "developer":
            pending_developer = value
            continue
        name, tool_input = calls[value]
        if name == "Bash":
            ran = scripts_in((tool_input or {}).get("command", ""), scripts)
            if ran:
                script_runs.update(ran)
                continue
        if not is_exploration(name, tool_input):
            continue
        summary = summarise(name, tool_input)
        if any(marker in summary for marker in own_files):
            skill_reads += 1
            continue
        number += 1
        explored += 1
        chars = results.get(value, 0)
        explored_chars += chars
        if pending_developer is not None:
            lines.append(f"--- developer: {pending_developer}")
            pending_developer = None
        lines.append(f"{number:>4}  {short_name(name):<24} {size(chars):>6}  {one_line(summary, INPUT_CHARS)}")

    out = []
    if not scripts_only:
        out.append(f"Exploration calls: {explored} (results {size(explored_chars)} chars) across {len(paths)} session(s);"
                   f" {skill_reads} skill-file reads left out")
    runs = ", ".join(f"{name} x{count}" for name, count in sorted(script_runs.items())) or "none"
    out.append(f"Script runs: {runs}")
    if not scripts_only and lines:
        out.append("")
        out.append(f"{'#':>4}  {'tool':<24} {'result':>6}  input")
        out.extend(lines)
    return "\n".join(out)


def main(argv):
    scripts_only = "--scripts-only" in argv
    paths = [a for a in argv if a != "--scripts-only"]
    if not paths:
        sys.exit("Usage: lookups.py [--scripts-only] <session.jsonl> [<session.jsonl> ...]")
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        sys.exit(f"No such transcript: {', '.join(missing)}")
    print(report(paths, scripts_only))


if __name__ == "__main__":
    main(sys.argv[1:])
