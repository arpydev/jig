#!/usr/bin/env python3
"""Check that splitting skills into the core and a pack lost nothing.

Usage: no_regression.py <config.json> [--approved <approved.json>]

The config lists the old skills, the new core and pack files, and the renames:
  {
    "old": ["path/to/old-skill", "path/to/file.md"],
    "new": ["skills/grilling", "steps/grill-<project>.md"],
    "map": {"mp-domain-modeling": "domain-modeling", "product owner": "developer"},
    "skip": ["upstream/"]
  }
Paths are relative to the config file, or absolute, or start with ~. Folders are read for
.md, .py and extensionless script files. "skip" leaves out any old or new file whose path
contains one of its strings.

Every old line is compared by its words only, after the renames in "map" (punctuation, case and
line wrapping don't count). A line is kept when its words appear in that order somewhere in the
new files. Lines that aren't kept are rewordings or removals: each is printed unless the
approvals file lists it, as {"old": "<the line as printed>", "why": "..."}.

Exit 0 when every old line is kept or approved, 1 otherwise.
"""
import json
import os
import re
import sys

EXTENSIONS = (".md", ".py", "")


def resolve(base, p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def files(paths, skip):
    out = []
    for p in paths:
        if os.path.isfile(p):
            found = [p]
        elif os.path.isdir(p):
            found = []
            for d, dirs, names in os.walk(p):
                dirs[:] = sorted(x for x in dirs if x not in ("__pycache__", "retros", ".git"))
                found += [os.path.join(d, n) for n in sorted(names) if os.path.splitext(n)[1] in EXTENSIONS and not n.startswith(".")]
        else:
            sys.exit(f"not found: {p}")
        out += [f for f in found if not any(s in f for s in skip)]
    return out


def words(text, renames=()):
    for old, new in renames:
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    return re.findall(r"[a-z0-9]+", text.lower())


def check(config_path, approved_path=None):
    base = os.path.dirname(os.path.abspath(config_path))
    with open(config_path) as f:
        cfg = json.load(f)
    renames = sorted(cfg.get("map", {}).items(), key=lambda kv: -len(kv[0]))
    skip = cfg.get("skip", [])
    approved = set()
    if approved_path:
        with open(approved_path) as f:
            approved = {" ".join(words(a["old"])) for a in json.load(f)}
    corpus = " " + " ".join(" ".join(words(open(f, encoding="utf-8").read())) for f in files([resolve(base, p) for p in cfg["new"]], skip)) + " "
    missing, kept, total, approved_hits = [], 0, 0, 0
    for path in files([resolve(base, p) for p in cfg["old"]], skip):
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        for n, line in enumerate(lines, 1):
            w = words(line, renames)
            if not w:
                continue
            total += 1
            if f" {' '.join(w)} " in corpus:
                kept += 1
            elif " ".join(words(line.strip())) in approved:
                approved_hits += 1
            else:
                missing.append((path, n, line.strip()))
    return total, kept, approved_hits, missing


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    approved = None
    if "--approved" in argv:
        approved = argv[argv.index("--approved") + 1]
    total, kept, approved_hits, missing = check(argv[0], approved)
    last = None
    for path, n, line in missing:
        if path != last:
            print(f"\n{path}")
            last = path
        print(f"  {n}: {line}")
    print(f"\n{total} old lines: {kept} kept (moved or unchanged), {approved_hits} approved rewordings, {len(missing)} not found")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
