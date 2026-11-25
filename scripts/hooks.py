#!/usr/bin/env python3
"""Merge hook entries from hooks.json files into Claude Code's settings.json.

Usage: hooks.py [--home <claude home>] [--dry-run] <hooks.json>...

Each hooks.json (the core's, and one per pack) has "files" (the hook scripts install.sh links
into <home>/hooks/) and "entries": {event, matcher (optional), command, timeout}. "{hooks}" in a
command becomes the hooks folder: ~/.claude/hooks for the default home, the full path otherwise.

Safe to rerun. An entry already in settings.json (same event, matcher and command) is left
alone. Entries it wrote are recorded in <home>/workflow-hooks.json with the hooks.json they came
from; an entry it wrote that its hooks.json no longer lists is removed. Entries it didn't write
are never touched, and neither are entries from a hooks.json not named in this run.
"""
import json
import os
import sys

RECORD = "workflow-hooks.json"


def hooks_dir(home):
    default = os.path.expanduser("~/.claude")
    return "~/.claude/hooks" if os.path.realpath(home) == os.path.realpath(default) else os.path.join(home, "hooks")


def read_json(path, empty):
    if not os.path.exists(path):
        return empty
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def wanted(sources, home):
    out = []
    for source in sources:
        for e in read_json(source, {}).get("entries", []):
            out.append({"source": source, "event": e["event"], "matcher": e.get("matcher"),
                        "command": e["command"].replace("{hooks}", hooks_dir(home)),
                        "timeout": e.get("timeout", 10)})
    return out


def key(e):
    return (e["event"], e.get("matcher"), e["command"])


def find_group(settings, event, matcher):
    for group in settings.get("hooks", {}).get(event, []):
        if group.get("matcher") == matcher:
            return group
    return None


def merge(settings, record, sources, entries):
    """Change settings in place; return (new record, lines to print)."""
    lines = []
    listed = {key(e) for e in entries}
    kept = []
    for r in record:
        if r["source"] in sources and key(r) not in listed:
            group = find_group(settings, r["event"], r.get("matcher"))
            if group:
                group["hooks"] = [h for h in group.get("hooks", []) if h.get("command") != r["command"]]
                if not group["hooks"]:
                    settings["hooks"][r["event"]].remove(group)
                    if not settings["hooks"][r["event"]]:
                        del settings["hooks"][r["event"]]
            lines.append(f"removed   {r['event']} {r.get('matcher') or '(all)'}: {r['command']}")
        else:
            kept.append(r)
    recorded = {key(r) for r in kept}
    for e in entries:
        group = find_group(settings, e["event"], e["matcher"])
        if group and any(h.get("command") == e["command"] for h in group.get("hooks", [])):
            lines.append(f"ok        {e['event']} {e['matcher'] or '(all)'}: {e['command']}")
        else:
            if not group:
                group = {"matcher": e["matcher"], "hooks": []} if e["matcher"] is not None else {"hooks": []}
                settings.setdefault("hooks", {}).setdefault(e["event"], []).append(group)
            group["hooks"].append({"type": "command", "command": e["command"], "timeout": e["timeout"]})
            lines.append(f"added     {e['event']} {e['matcher'] or '(all)'}: {e['command']}")
        if key(e) not in recorded:
            kept.append({k: e[k] for k in ("source", "event", "matcher", "command")})
            recorded.add(key(e))
    return kept, lines


def main(argv):
    home = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    dry = False
    sources = []
    i = 0
    while i < len(argv):
        if argv[i] == "--home":
            home = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--dry-run":
            dry = True
        else:
            sources.append(os.path.realpath(argv[i]))
        i += 1
    if not sources:
        print(__doc__, file=sys.stderr)
        return 2
    settings_path = os.path.join(home, "settings.json")
    record_path = os.path.join(home, RECORD)
    settings = read_json(settings_path, {})
    record, lines = merge(settings, read_json(record_path, []), sources, wanted(sources, home))
    for line in lines:
        print(("would be " + line) if dry and not line.startswith("ok") else line)
    if not dry:
        os.makedirs(home, exist_ok=True)
        write_json(settings_path, settings)
        write_json(record_path, record)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
