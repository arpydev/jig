#!/usr/bin/env python3
"""Print what can be proven about a repository, for the setup-workflow skill.

Usage: detect.py [--repo DIR]

Prints JSON: main checkout, remote, package scripts, glossary and ADR candidates, existing
settings, routes and features from tracked files. Only tracked files are read, so ignored
output never shows up. Anything it can't prove (team or personal, where run data goes) is
left for the developer.
"""
import json
import os
import re
import subprocess
import sys

ROUTE = re.compile(r"(^|/)app/(.*/)?(page|route)\.[jt]sx?$")
TEST = re.compile(r"\.(test|spec)\.[jt]sx?$|(^|/)test_[^/]+\.py$")


def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def main(argv):
    repo = argv[argv.index("--repo") + 1] if "--repo" in argv else "."
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        sys.exit(f"not a git repository: {repo}")
    root = os.path.dirname(common)
    files = git(root, "ls-files").splitlines()
    remote = git(root, "remote", "get-url", "origin")
    m = re.search(r"github\.com[:/](.+?)(\.git)?$", remote)
    out = {
        "root": root,
        "remote": remote or None,
        "githubRepo": m.group(1) if m else None,
        "settingsExists": os.path.exists(os.path.join(root, ".claude", "workflow.json")),
        "packageScripts": {},
        "glossary": [f for f in files if os.path.basename(f) in ("GLOSSARY.md", "CONTEXT.md", "GLOSSARY-MAP.md")],
        "adrDirs": sorted({os.path.dirname(f) for f in files if re.search(r"(^|/)adr/[^/]+\.md$", f)}),
        "verifySkills": sorted({f.split("/")[2] for f in files if f.startswith(".claude/skills/verify-")}),
        "routes": [f for f in files if ROUTE.search(f)],
        "features": {},
        "testFiles": len([f for f in files if TEST.search(f)]),
    }
    claude = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    packs = os.path.join(claude, "workflow-packs")
    out["packProjectSkills"] = {}
    if os.path.exists(packs):
        with open(packs) as f:
            for pack in filter(None, f.read().splitlines()):
                pj = os.path.join(pack, "pack.json")
                if os.path.exists(pj):
                    with open(pj) as g:
                        names = json.load(g).get("projectSkills", [])
                    out["packProjectSkills"].update({n: os.path.join(pack, "skills", n) for n in names})
    out["linkedSkills"] = sorted(n for n in os.listdir(os.path.join(root, ".claude", "skills"))
                                 if os.path.islink(os.path.join(root, ".claude", "skills", n))) if os.path.isdir(os.path.join(root, ".claude", "skills")) else []
    pkg = os.path.join(root, "package.json")
    if os.path.exists(pkg):
        with open(pkg) as f:
            scripts = json.load(f).get("scripts", {})
        out["packageScripts"] = {k: v for k, v in scripts.items() if re.match(r"(check|test|lint|typecheck|build)(:|$)", k)}
        lock = {"pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "package-lock.json": "npm", "bun.lockb": "bun"}
        out["packageManager"] = next((v for k, v in lock.items() if k in files), "npm")
    feature_dirs = sorted({m.group(1) for f in files for m in [re.match(r"((?:.*/)?features/[^/]+)/", f)] if m})
    for d in feature_dirs:
        out["features"][d] = sorted(f for f in files if f.startswith(d + "/") and TEST.search(f))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
