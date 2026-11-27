#!/usr/bin/env python3
"""Read and check a repository's workflow settings (.claude/workflow.json).

Usage (run from anywhere inside the repository, or pass --repo):
  settings.py path                 print the settings file's path (always in the main checkout)
  settings.py get <dotted.key>     print one value; exit 1 if it is missing
  settings.py set <dotted.key> <value>
                                   save a text value, keeping every other setting; refuse it
                                   when the result fails check
  settings.py check                check the file against the format; exit 1 on any problem
  settings.py exclude              hide the settings and verify skill with .git/info/exclude
                                   (only when "committed" is false; safe to rerun)
  settings.py never-commit         print the paths the core must never stage
  settings.py link                 link the projectSkills into .claude/skills (safe to rerun)
  settings.py steps <step> [--paths]
                                   print the step's additions, one per line: a file's absolute path
                                   or skill:<name>; prints nothing when there are no settings.
                                   --paths prints each skill as its SKILL.md path instead, for an
                                   agent with no Skill tool to read
  settings.py model <role>         print the role's model (session, sonnet, opus or haiku): the
                                   project's override, or the core default; works without settings

The format is in ../references/settings.md.
"""
import json
import os
import subprocess
import sys

STEPS = ["grill", "domain", "design", "spec", "tickets", "plan", "build", "deploy", "verify", "review", "retro"]
TRACKERS = {"github": [], "gitlab": [], "local": ["dir"], "jira": ["site", "keyPattern"], "other": []}
MODELS = ("session", "sonnet", "opus", "haiku")
ROLES = {
    "implementer": "session",
    "explorer": "sonnet",
    "merger": "sonnet",
    "standardsReviewer": "sonnet",
    "specReviewer": "sonnet",
    "correctnessReviewer": "opus",
}
REQUIRED = ["version", "committed", "tracker", "checks", "docs", "runData", "verifySkill"]
SETTINGS = os.path.join(".claude", "workflow.json")
RATCHET = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ratchet.py")


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def main_checkout(repo):
    try:
        common = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail(f"not a git repository: {repo}")
    return os.path.dirname(common)


def load(root):
    path = os.path.join(root, SETTINGS)
    if not os.path.exists(path):
        fail(f"no settings at {path}; run the setup-workflow skill")
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            fail(f"{path} is not valid JSON: {e}")


def expand(root, p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(root, p)


def skill_dirs(root):
    claude = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    return (os.path.join(root, ".claude", "skills"), os.path.join(claude, "skills"))


def skill_exists(root, name):
    return any(os.path.isdir(os.path.join(d, name)) for d in skill_dirs(root))


def skill_path(root, name):
    """The SKILL.md a skill name resolves to: the project's copy first, as Claude Code loads it."""
    for d in skill_dirs(root):
        p = os.path.join(d, name, "SKILL.md")
        if os.path.isfile(p):
            return os.path.realpath(p)
    fail(f"skill not installed: {name}")


def agent_exists(root, name):
    claude = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    return any(os.path.isfile(os.path.join(d, name + ".md")) for d in (os.path.join(claude, "agents"), os.path.join(root, ".claude", "agents")))


def problems(root, s):
    out = [f"missing key: {k}" for k in REQUIRED if k not in s]
    if out:
        return out
    if s["version"] != 1:
        out.append(f"unknown version: {s['version']}")
    if not isinstance(s["committed"], bool):
        out.append("committed must be true or false")
    kind = s["tracker"].get("kind")
    if kind not in TRACKERS:
        out.append(f"tracker.kind must be one of {', '.join(TRACKERS)}")
    else:
        out += [f"tracker.{k} is required for {kind}" for k in TRACKERS[kind] if not s["tracker"].get(k)]
    if not isinstance(s["checks"], str) or not s["checks"].strip():
        out.append("checks must be the command that runs the project's checks")
    if "tickets" in s["tracker"] and not (isinstance(s["tracker"]["tickets"], str) and s["tracker"]["tickets"].strip()):
        out.append("tracker.tickets must say how to fetch the tickets: a command or an instruction")
    n = s.get("implementers", 1)
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        out.append("implementers must be a whole number of 1 or more")
    if "worktreeSetup" in s and not (isinstance(s["worktreeSetup"], str) and s["worktreeSetup"].strip()):
        out.append("worktreeSetup must be the command run in each new worktree")
    if "workerAgent" in s:
        name = s["workerAgent"]
        if not (isinstance(name, str) and name.strip()):
            out.append("workerAgent must be an agent's name")
        elif not agent_exists(root, name):
            out.append(f"workerAgent: agent not installed: {name}")
    if "ratchet" in s:
        copy = expand(root, s["ratchet"])
        if not os.path.isfile(copy):
            out.append(f"ratchet: file not found: {s['ratchet']}")
        else:
            with open(copy, "rb") as a, open(RATCHET, "rb") as b:
                if a.read() != b.read():
                    out.append(f"ratchet: {s['ratchet']} differs from the core's copy; "
                               f"run `ratchet.py install {root} --to {s['ratchet']}`")
    for k in ("glossary", "adr"):
        if not s["docs"].get(k):
            out.append(f"docs.{k} is required")
    for step, adds in s.get("steps", {}).items():
        if step not in STEPS:
            out.append(f"steps.{step}: unknown step (use one of {', '.join(STEPS)})")
            continue
        for a in adds:
            if a.startswith("skill:"):
                if not skill_exists(root, a[6:]):
                    out.append(f"steps.{step}: skill not installed: {a[6:]}")
            elif not os.path.exists(expand(root, a)):
                out.append(f"steps.{step}: file not found: {a}")
    for p in s.get("projectSkills", []):
        if not os.path.isfile(os.path.join(expand(root, p), "SKILL.md")):
            out.append(f"projectSkills: not a skill folder: {p}")
    ast = s.get("ast", {})
    if not isinstance(ast, dict) or not all(isinstance(t, str) and t.strip() for t in ast.values()):
        out.append("ast must map each language to its tool, such as {\"typescript\": \"node_modules/typescript\"}")
    for role, model in s.get("models", {}).items():
        if role not in ROLES:
            out.append(f"models.{role}: unknown role (use one of {', '.join(ROLES)})")
        if model not in MODELS:
            out.append(f"models.{role}: unknown model {model}")
    return out


def save(root, s, key, value):
    *parents, last = key.split(".")
    v = s
    for part in parents:
        v = v.setdefault(part, {})
        if not isinstance(v, dict):
            fail(f"{key}: {part} is not an object")
    v[last] = value
    out = problems(root, s)
    if out:
        fail(f"not saved: {key} {value} would leave these problems:\n" + "\n".join(out))
    with open(os.path.join(root, SETTINGS), "w") as f:
        json.dump(s, f, indent=2)
        f.write("\n")
    print(f"saved {key}")


def never_commit(s):
    if s.get("committed"):
        return []
    skills = [s.get("verifySkill", "verify-*")] + [os.path.basename(os.path.normpath(p)) for p in s.get("projectSkills", [])]
    return [SETTINGS] + [os.path.join(".claude", "skills", n) for n in skills]


def link(root, s):
    bad = 0
    for p in s.get("projectSkills", []):
        src = os.path.normpath(expand(root, p))
        dest = os.path.join(root, ".claude", "skills", os.path.basename(src))
        if os.path.islink(dest) and os.path.realpath(dest) == os.path.realpath(src):
            print(f"ok        {dest}")
        elif os.path.lexists(dest):
            print(f"CONFLICT  {dest} exists and is not a link to {src}")
            bad += 1
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            os.symlink(src, dest)
            print(f"linked    {dest} -> {src}")
    if bad:
        sys.exit(1)


def exclude(root, s):
    paths = never_commit(s)
    if not paths:
        print("committed is true; nothing to exclude")
        return
    ex = os.path.join(root, ".git", "info", "exclude")
    os.makedirs(os.path.dirname(ex), exist_ok=True)
    have = []
    if os.path.exists(ex):
        with open(ex) as f:
            have = f.read().splitlines()
    new = ["/" + p for p in paths if "/" + p not in have]
    if new:
        with open(ex, "a") as f:
            f.write("".join(line + "\n" for line in new))
    print(f"excluded: {', '.join(paths)}" + ("" if new else " (already)"))


def main(argv):
    repo = "."
    if "--repo" in argv:
        i = argv.index("--repo")
        repo = argv[i + 1]
        del argv[i:i + 2]
    if not argv:
        fail(__doc__)
    root = main_checkout(repo)
    cmd = argv[0]
    if cmd == "path":
        print(os.path.join(root, SETTINGS))
        return
    if cmd == "steps":
        paths = "--paths" in argv
        argv = [a for a in argv if a != "--paths"]
        if len(argv) < 2 or argv[1] not in STEPS:
            fail(f"usage: settings.py steps <{'|'.join(STEPS)}>")
        if not os.path.exists(os.path.join(root, SETTINGS)):
            print("no workflow settings in this repository; no step additions", file=sys.stderr)
            return
        for a in load(root).get("steps", {}).get(argv[1], []):
            if a.startswith("skill:"):
                print(skill_path(root, a[6:]) if paths else a)
            else:
                print(expand(root, a))
        return
    if cmd == "model":
        if len(argv) < 2 or argv[1] not in ROLES:
            fail(f"usage: settings.py model <{'|'.join(ROLES)}>")
        has = os.path.exists(os.path.join(root, SETTINGS))
        print((load(root).get("models", {}) if has else {}).get(argv[1], ROLES[argv[1]]))
        return
    s = load(root)
    if cmd == "get":
        if len(argv) < 2:
            fail("usage: settings.py get <dotted.key>")
        v = s
        for part in argv[1].split("."):
            if not isinstance(v, dict) or part not in v:
                fail(f"not set: {argv[1]}")
            v = v[part]
        print(v if isinstance(v, str) else json.dumps(v))
    elif cmd == "set":
        if len(argv) < 3:
            fail("usage: settings.py set <dotted.key> <value>")
        save(root, s, argv[1], argv[2])
    elif cmd == "check":
        out = problems(root, s)
        for p in out:
            print(p)
        if out:
            sys.exit(1)
        print("ok")
    elif cmd == "exclude":
        exclude(root, s)
    elif cmd == "link":
        link(root, s)
    elif cmd == "never-commit":
        print("\n".join(never_commit(s)))
    else:
        fail(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
