#!/usr/bin/env python3
"""The developer's knowledge map for one project: ~/.claude/knowledge/<project>.md.

Usage (from inside the repository, or with --repo):
  knowledge.py status [PATH ...]   level, last evidence and staleness of the areas covering these paths
                                   (every area when none are given); paths no area covers are listed
  knowledge.py record AREA --level LEVEL --evidence TEXT [--paths a,b] [--date YYYY-MM-DD]
                                   add a dated evidence line and set the level; a new area needs --paths
  knowledge.py path                print the map's path

<project> is the main checkout's folder name, so worktrees share one map. The map lives outside every
repository because it is about the developer, not the code. KNOWLEDGE_DIR overrides the folder.

An area is re-check due when its newest evidence is older than STALE_DAYS, or its paths have had
STALE_COMMITS or more commits since. Both are worked out here on every run, never stored.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

LEVELS = ["new", "followed it", "can explain", "can teach"]
EXPLAIN_BELOW = "can explain"  # below this level, explain and ask before acting
STALE_DAYS = 90
STALE_COMMITS = 20
EVIDENCE = re.compile(r"^- (\d{4}-\d{2}-\d{2}): (.+)$")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True).stdout.strip()


def main_checkout(repo):
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        sys.exit(f"knowledge.py: {repo} is not in a git repository")
    return os.path.dirname(common.rstrip("/"))


def map_path(repo):
    folder = os.environ.get("KNOWLEDGE_DIR") or os.path.expanduser("~/.claude/knowledge")
    return os.path.join(folder, os.path.basename(main_checkout(repo)) + ".md")


def load(path):
    """Areas in file order: {name: {"level", "paths", "evidence": [(date, text)]}}."""
    areas, current = {}, None
    if not os.path.exists(path):
        return areas
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in lines:
        if line.startswith("## "):
            current = areas.setdefault(line[3:].strip(), {"level": "new", "paths": [], "evidence": []})
        elif current is None:
            continue
        elif line.startswith("- Level: "):
            current["level"] = line[9:].strip()
        elif line.startswith("- Paths: "):
            current["paths"] = [p.strip() for p in line[9:].split(",") if p.strip()]
        elif m := EVIDENCE.match(line):
            current["evidence"].append((m.group(1), m.group(2)))
    return areas


def save(path, project, areas):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = [f"# Knowledge map: {project}", "",
           "Written by `knowledge.py record`. A level rises only on dated evidence the developer approved.", ""]
    for name, a in areas.items():
        out += [f"## {name}", "", f"- Level: {a['level']}", f"- Paths: {', '.join(a['paths'])}"]
        out += [f"- {d}: {t}" for d, t in a["evidence"]] + [""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def covers(area, path):
    path = path.removeprefix("./")
    return any(path == p.rstrip("/") or path.startswith(p) for p in area["paths"])


def staleness(repo, area, today):
    """(last evidence date or None, days since, commits since, why a re-check is due or None)."""
    if not area["evidence"]:
        return None, None, None, "no evidence yet"
    last = max(d for d, _ in area["evidence"])
    days = (today - datetime.date.fromisoformat(last)).days
    commits = int(git(repo, "rev-list", "--count", f"--since={last}", "HEAD", "--", *area["paths"]) or 0)
    if days > STALE_DAYS:
        return last, days, commits, f"evidence is {days} days old"
    if commits >= STALE_COMMITS:
        return last, days, commits, f"{commits} commits since"
    return last, days, commits, None


def needs_explaining(repo, area, today):
    """Why this area needs explaining and an explain-back question, or None when the developer knows it."""
    if LEVELS.index(area["level"]) < LEVELS.index(EXPLAIN_BELOW):
        return f"level is {area['level']}"
    return staleness(repo, area, today)[3]


def mentioned(name, area, text):
    """Does the text name this area, by its name (loosely: case, hyphens, a plural s) or one of its paths?"""
    flat = re.sub(r"[^a-z0-9]", "", text.lower())
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    stems = {key, key[:-1] if key.endswith("s") and len(key) > 4 else key}
    return any(s and s in flat for s in stems) or any(p.rstrip("/") in text for p in area["paths"])


def warnings(text, repo, today=None):
    """One line per area the text names that the developer doesn't yet know well. Used by the outbound check."""
    today = today or datetime.date.today()
    areas = load(map_path(repo))
    out = []
    for name, area in areas.items():
        if mentioned(name, area, text) and (why := needs_explaining(repo, area, today)):
            out.append(f"{name} ({why})")
    return out


def status(repo, paths, today):
    areas = load(map_path(repo))
    chosen = [n for n, a in areas.items() if not paths or any(covers(a, p) for p in paths)]
    for name in chosen:
        a = areas[name]
        last, days, commits, due = staleness(repo, a, today)
        seen = f"last evidence {last} ({days} days, {commits} commits since)" if last else "no evidence yet"
        act = ("explain and ask first" if needs_explaining(repo, a, today) else "knows it") + \
              (f"; re-check due: {due}" if due and last else "")
        print(f"{name} | {a['level']} | {seen} | {act}")
    for p in paths:
        if not any(covers(a, p) for a in areas.values()):
            print(f"no area | {p} | treat as new; propose an area once the developer has worked through it")
    if not chosen and not paths:
        print(f"no areas yet in {map_path(repo)}")


def record(repo, name, level, evidence, paths, date):
    if level not in LEVELS:
        sys.exit(f"knowledge.py: level must be one of: {', '.join(LEVELS)}")
    path = map_path(repo)
    areas = load(path)
    if name not in areas and not paths:
        sys.exit(f"knowledge.py: {name} is a new area; give --paths")
    area = areas.setdefault(name, {"level": level, "paths": [], "evidence": []})
    area["level"] = level
    if paths:
        area["paths"] = [p.strip() for p in paths.split(",") if p.strip()]
    area["evidence"].append((date, f"({level}) {evidence}"))
    save(path, os.path.basename(main_checkout(repo)), areas)
    print(f"recorded {name}: {level}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="The developer's knowledge map for this project.")
    ap.add_argument("--repo", default=os.getcwd())
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("status")
    st.add_argument("paths", nargs="*")
    rec = sub.add_parser("record")
    rec.add_argument("area")
    rec.add_argument("--level", required=True)
    rec.add_argument("--evidence", required=True)
    rec.add_argument("--paths")
    rec.add_argument("--date", default=datetime.date.today().isoformat())
    sub.add_parser("path")
    args = ap.parse_args(argv)
    if args.cmd == "status":
        status(args.repo, args.paths, datetime.date.today())
    elif args.cmd == "record":
        record(args.repo, args.area, args.level, args.evidence, args.paths, args.date)
    else:
        print(map_path(args.repo))


if __name__ == "__main__":
    main()
