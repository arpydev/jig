#!/usr/bin/env python3
"""Check that skills name only scripts, files, step files and skills that exist.

Usage: skill_refs.py [--pack <dir>]... [--known <skill>]...

Reads every .md file in the core's skills and in each pack's skills (not `upstream/`) and prints
one line per problem:
- `~/.claude/skills/<skill>/<path>` where <skill> isn't installed user-wide (a pack's project
  skill is linked into each repository, not into ~/.claude/skills) or <path> is missing from it;
- `<this skill's folder>/<path>`, a markdown link, or a backticked `scripts/`, `references/` or
  `templates/` path missing from the skill's folder (or, for a link, the file's own folder;
  links inside code fences are examples and skipped); "the `x` skill's `<path>`" is looked up in x;
- a pack's `steps/<file>.md` missing from the pack;
- a skill loaded by name (the Skill tool with `x`, load the `x`, the `x` skill) that no core or
  pack skill provides and no --known names (project skills kept elsewhere, plugin skills).
Placeholders (anything with `<`, `*` or `{`) are skipped. Exit 1 when anything is printed.
"""
import argparse
import json
import os
import re
import sys

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HOME_PATH = re.compile(r"~/\.claude/skills/([A-Za-z0-9_.-]+)/([^\s`)\"']+)")
OWN_PATH = re.compile(r"<this skill's folder>/([^\s`)\"']+)")
LINK = re.compile(r"\]\(([^)\s]+)\)")
TICKED = re.compile(r"`((?:scripts|references|templates)/[^`\s]+)`")
OTHER_SKILL = re.compile(r"`([a-z][a-z0-9-]*)` skill's `((?:scripts|references|templates)/[^`\s]+)`")
FENCE = re.compile(r"^```.*?^```", re.S | re.M)
STEP_FILE = re.compile(r"\bsteps/([a-z0-9-]+\.md)\b")
SKILL_NAME = [
    re.compile(r"Skill tool with `([a-z][a-z0-9:-]*)`"),
    re.compile(r"\b[Ll]oads? (?:the )?`([a-z][a-z0-9:-]*)`"),
    re.compile(r"`([a-z][a-z0-9:-]*)` skill\b"),
]


def placeholder(path):
    return any(c in path for c in "<*{")


def clean(path):
    return path.split("#")[0].rstrip(".,;:")


def skills_in(folder):
    if not os.path.isdir(folder):
        return {}
    return {n: os.path.join(folder, n) for n in sorted(os.listdir(folder))
            if os.path.isfile(os.path.join(folder, n, "SKILL.md"))}


def md_files(skill_dir):
    for d, dirs, names in os.walk(skill_dir):
        dirs[:] = sorted(x for x in dirs if x not in ("upstream", "__pycache__"))
        for n in sorted(names):
            if n.endswith(".md"):
                yield os.path.join(d, n)


def check(packs=(), known=()):
    core = skills_in(os.path.join(CORE, "skills"))
    owned = {}  # skill -> (dir, pack root or None)
    user_wide = dict(core)
    project = set()
    for name, path in core.items():
        owned[name] = (path, None)
    for pack in packs:
        pack_json = os.path.join(pack, "pack.json")
        scoped = set(json.load(open(pack_json)).get("projectSkills", [])) if os.path.exists(pack_json) else set()
        for name, path in skills_in(os.path.join(pack, "skills")).items():
            owned.setdefault(name, (path, pack))
            if name in scoped:
                project.add(name)
            else:
                user_wide.setdefault(name, path)
    names = set(owned) | set(known)
    problems = []
    for name, (skill_dir, pack) in sorted(owned.items()):
        for f in md_files(skill_dir):
            text = open(f, encoding="utf-8").read()
            where = os.path.relpath(f, pack or os.path.dirname(CORE))

            def bad(line_of, msg):
                line = text.count("\n", 0, line_of) + 1
                problems.append((where, line, msg))

            for m in HOME_PATH.finditer(text):
                skill, rest = m.group(1), clean(m.group(2))
                if skill in project:
                    bad(m.start(), f"`~/.claude/skills/{skill}` is a project skill, not installed user-wide; "
                                   f"write `<this skill's folder>/{rest}`" if skill == name else
                        f"`~/.claude/skills/{skill}` is a project skill, not installed user-wide")
                elif skill not in user_wide:
                    bad(m.start(), f"no skill `{skill}` is installed user-wide")
                elif not placeholder(rest) and not os.path.exists(os.path.join(user_wide[skill], rest)):
                    bad(m.start(), f"`{skill}` has no `{rest}`")
            for m in OWN_PATH.finditer(text):
                rest = clean(m.group(1))
                if not placeholder(rest) and not os.path.exists(os.path.join(skill_dir, rest)):
                    bad(m.start(), f"`{name}` has no `{rest}`")
            fenced = [(m.start(), m.end()) for m in FENCE.finditer(text)]
            for m in LINK.finditer(text):
                if any(a <= m.start() < b for a, b in fenced):
                    continue
                target = clean(m.group(1))
                if not target or placeholder(target) or re.match(r"^(\w+:|/|~|#)", target):
                    continue
                if not os.path.exists(os.path.join(os.path.dirname(f), target)):
                    bad(m.start(), f"link to missing `{target}`")
            elsewhere = set()
            for m in OTHER_SKILL.finditer(text):
                skill, rest = m.group(1), clean(m.group(2))
                elsewhere.add(m.start(2) - 1)
                if skill not in owned:
                    bad(m.start(), f"no skill `{skill}`")
                elif not placeholder(rest) and not os.path.exists(os.path.join(owned[skill][0], rest)):
                    bad(m.start(), f"`{skill}` has no `{rest}`")
            for m in TICKED.finditer(text):
                rest = clean(m.group(1))
                if placeholder(rest) or m.start() in elsewhere:
                    continue
                if not any(os.path.exists(os.path.join(base, rest)) for base in (skill_dir, os.path.dirname(f))):
                    bad(m.start(), f"`{name}` has no `{rest}`")
            if pack:
                for m in STEP_FILE.finditer(text):
                    if not os.path.exists(os.path.join(pack, "steps", m.group(1))):
                        bad(m.start(), f"no step file `steps/{m.group(1)}`")
            for pattern in SKILL_NAME:
                for m in pattern.finditer(text):
                    if m.group(1) not in names:
                        bad(m.start(), f"no skill `{m.group(1)}`")
    return [f"{w}:{n}: {msg}" for w, n, msg in sorted(problems)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pack", action="append", default=[])
    ap.add_argument("--known", action="append", default=[])
    args = ap.parse_args(argv)
    problems = check(args.pack, args.known)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
