#!/usr/bin/env python3
"""SessionStart hook: tell the user when a newer Jig release is out.

Compares the core's current release tag with the newest vX.Y.Z tag on its origin remote, and if
the remote is ahead, shows the user one line naming update.sh. The remote is asked at most once a
day (git ls-remote, 3s timeout); the answer is cached in <claude home>/workflow-update-check.json,
which update.sh deletes. Owners of the core (workflow-core.json "owner": true) are never prompted,
because they work on main. Any failure (offline, no remote, no tags) is silent.
CLAUDE_HOME overrides ~/.claude; JIG_CORE overrides the core folder (both used by the tests).
"""
import json
import os
import re
import subprocess
import sys
import time

DAY = 24 * 60 * 60
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def version(tag):
    m = TAG.match(tag or "")
    return tuple(int(n) for n in m.groups()) if m else None


def git(core, *args, timeout=3):
    return subprocess.run(["git", "-C", core, *args], capture_output=True, text=True,
                          timeout=timeout, check=True).stdout.strip()


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def newest_remote_tag(core):
    out = git(core, "ls-remote", "--tags", "--refs", "origin", "v*")
    tags = [line.rsplit("refs/tags/", 1)[-1] for line in out.splitlines()]
    tags = [t for t in tags if version(t)]
    return max(tags, key=version) if tags else None


def releases_url(core):
    url = git(core, "remote", "get-url", "origin")
    m = re.match(r"^(?:https://github\.com/|git@github\.com:)(.+?)(?:\.git)?$", url)
    return f"https://github.com/{m.group(1)}/releases" if m else None


def main():
    home = os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude")
    core = os.environ.get("JIG_CORE") or os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if read_json(os.path.join(home, "workflow-core.json")).get("owner"):
        return
    cache_path = os.path.join(home, "workflow-update-check.json")
    cache = read_json(cache_path)
    latest = cache.get("latest")
    if time.time() - cache.get("checked", 0) >= DAY:
        try:
            latest = newest_remote_tag(core)
        except (OSError, subprocess.SubprocessError):
            pass  # offline or no remote: keep the last answer and try again tomorrow
        try:
            with open(cache_path, "w") as f:
                json.dump({"checked": int(time.time()), "latest": latest}, f)
        except OSError:
            pass
    if not version(latest):
        return
    try:
        current = git(core, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    except subprocess.SubprocessError:
        current = None
    if version(current) and version(current) >= version(latest):
        return
    have = f"you have {current}" if version(current) else "you are not on a release"
    msg = f"Jig {latest} is out ({have}). To update, run: {os.path.join(core, 'update.sh')}"
    try:
        url = releases_url(core)
        if url:
            msg += f" (what changed: {url})"
    except (OSError, subprocess.SubprocessError):
        pass
    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    try:
        sys.stdin.read()
        main()
    except Exception:
        pass
    sys.exit(0)
