#!/usr/bin/env python3
"""Write the skeleton of a project's verification skill from what detect.py proves.

Usage: verify_skeleton.py <skill-name> [--repo DIR] [--force]

Writes <main checkout>/.claude/skills/<skill-name>/SKILL.md with one feature-map row per
feature folder (code and tests filled in) and the routes still to be mapped. "How to check" is
left empty: each run fills a feature's row by hand the first time it touches it. Refuses to
overwrite an existing skill unless --force.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv):
    if not argv or argv[0].startswith("--"):
        sys.exit(__doc__)
    name = argv[0]
    repo = argv[argv.index("--repo") + 1] if "--repo" in argv else "."
    facts = json.loads(subprocess.run([sys.executable, os.path.join(HERE, "detect.py"), "--repo", repo],
                                      capture_output=True, text=True, check=True).stdout)
    path = os.path.join(facts["root"], ".claude", "skills", name, "SKILL.md")
    if os.path.exists(path) and "--force" not in argv:
        sys.exit(f"already exists: {path} (pass --force to replace)")
    with open(os.path.join(HERE, "..", "templates", "verify-SKILL.md")) as f:
        template = f.read()
    rows = "\n".join(f"| {os.path.basename(d)} | `{d}/` | {len(t)} test files | |" for d, t in facts["features"].items())
    routes = "\n".join(f"- `{r}`" for r in facts["routes"]) or "- (none found)"
    text = template.replace("{{name}}", name).replace("{{rows}}", rows or "| | | | |").replace("{{routes}}", routes)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    print(f"wrote {path}: {len(facts['features'])} features, {len(facts['routes'])} routes to map")


if __name__ == "__main__":
    main(sys.argv[1:])
