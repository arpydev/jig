#!/usr/bin/env python3
"""Lint rule ratchet: a rule's breaches can only go down.

A rule is any shell command that prints one breach per line, as `path` or `path:line...`
(a grep, or a linter's output). Each rule is `.ratchet/<rule>.json` at the repository root,
holding the command, the reason and the per-file baseline. Commit the folder.

Usage (from anywhere inside the repository):
  ratchet.py add <rule> --command <cmd> --reason <why>
                       record today's breaches as the baseline; refuses an existing rule
  ratchet.py check     run every rule; exit 1 if a file has more breaches than its baseline,
                       or fewer (then run `lower` and commit the baseline)
  ratchet.py lower     lower each baseline to today's counts; never raises one
  ratchet.py list      print each rule, its total and its reason
  ratchet.py install <repo> [--to scripts/ratchet.py]
                       copy this script into a repository, so its checks and CI can run it

Standard library only. The core's copy (setup-workflow/scripts/ratchet.py) is the master;
`settings.py check` fails when a project's copy (the `ratchet` setting) differs from it.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

FOLDER = ".ratchet"


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def root():
    try:
        return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail("not inside a git repository")


def rule_path(top, name):
    return os.path.join(top, FOLDER, f"{name}.json")


def rules(top):
    folder = os.path.join(top, FOLDER)
    if not os.path.isdir(folder):
        return []
    out = []
    for f in sorted(os.listdir(folder)):
        if f.endswith(".json"):
            with open(os.path.join(folder, f)) as fh:
                out.append(json.load(fh))
    return out


def count(top, command):
    r = subprocess.run(command, shell=True, cwd=top, capture_output=True, text=True)
    if r.returncode and not r.stdout.strip() and r.stderr.strip():
        fail(f"rule command failed ({r.returncode}): {command}\n{r.stderr.strip()}")
    counts = {}
    for line in r.stdout.splitlines():
        if line.strip():
            path = os.path.normpath(line.split(":", 1)[0].strip())
            counts[path] = counts.get(path, 0) + 1
    return counts


def compare(counts, baseline):
    files = sorted(set(counts) | set(baseline))
    up = [(f, counts.get(f, 0), baseline.get(f, 0)) for f in files if counts.get(f, 0) > baseline.get(f, 0)]
    down = [(f, counts.get(f, 0), baseline.get(f, 0)) for f in files if counts.get(f, 0) < baseline.get(f, 0)]
    return up, down


def save(top, rule):
    path = rule_path(top, rule["rule"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rule["baseline"] = {f: n for f, n in sorted(rule["baseline"].items()) if n > 0}
    with open(path, "w") as fh:
        json.dump(rule, fh, indent=2)
        fh.write("\n")


def add(top, name, command, reason):
    if os.path.exists(rule_path(top, name)):
        fail(f"rule {name} already exists; change {FOLDER}/{name}.json by hand")
    if not reason.strip():
        fail("a rule needs its reason")
    baseline = count(top, command)
    save(top, {"rule": name, "command": command, "reason": reason, "baseline": baseline})
    print(f"added {name}: {sum(baseline.values())} existing breaches in {len(baseline)} files are the baseline")


def check(top):
    bad = False
    for rule in rules(top):
        up, down = compare(count(top, rule["command"]), rule["baseline"])
        if up:
            bad = True
            print(f"{rule['rule']}: more breaches than the baseline allows ({rule['reason']}):")
            print("\n".join(f"  {f}: {n} (allowed {a})" for f, n, a in up))
        if down:
            bad = True
            print(f"{rule['rule']}: breaches were fixed, so the baseline can come down. "
                  f"Run `ratchet.py lower` and commit {FOLDER}/:")
            print("\n".join(f"  {f}: {n} (baseline {a})" for f, n, a in down))
    if bad:
        sys.exit(1)
    print("ok")


def lower(top):
    for rule in rules(top):
        counts = count(top, rule["command"])
        up, down = compare(counts, rule["baseline"])
        if up:
            fail(f"{rule['rule']}: breaches went up; fix them before lowering (run `ratchet.py check`)")
        rule["baseline"] = {f: min(n, counts.get(f, 0)) for f, n in rule["baseline"].items()}
        save(top, rule)
        print(f"{rule['rule']}: {sum(rule['baseline'].values())}" + (" (lowered)" if down else ""))


def install(repo, to):
    dest = os.path.join(repo, to)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(os.path.realpath(__file__), dest)
    os.chmod(dest, 0o755)
    print(f"copied to {dest}; set \"ratchet\": \"{to}\" in the settings and add `python3 {to} check` to the checks")


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("rule")
    a.add_argument("--command", required=True)
    a.add_argument("--reason", required=True)
    for name in ("check", "lower", "list"):
        sub.add_parser(name)
    i = sub.add_parser("install")
    i.add_argument("repo")
    i.add_argument("--to", default=os.path.join("scripts", "ratchet.py"))
    args = p.parse_args(argv)
    if args.cmd == "install":
        install(args.repo, args.to)
        return
    top = root()
    if args.cmd == "add":
        add(top, args.rule, args.command, args.reason)
    elif args.cmd == "check":
        check(top)
    elif args.cmd == "lower":
        lower(top)
    else:
        for rule in rules(top):
            print(f"{rule['rule']}: {sum(rule['baseline'].values())} ({rule['reason']})")


if __name__ == "__main__":
    main(sys.argv[1:])
