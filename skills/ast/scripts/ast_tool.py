#!/usr/bin/env python3
"""Find the AST tool a repository uses for one language.

Usage (run from anywhere inside the repository, or pass --repo):
  ast_tool.py find <language>      print the tool to use and exit 0. Looks first in the repository
                                   (its node_modules), then at `ast.<language>` in the project
                                   settings. Exit 2 with each candidate on its own line when several
                                   are installed and none is chosen; exit 3 when there is none.
                                   Either way the developer picks; save their pick
  ast_tool.py save <language> <tool>
                                   save the developer's pick as `ast.<language>` in the project
                                   settings, so the next `find` returns it
"""
import os
import subprocess
import sys

SETTINGS_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                           "setup-workflow", "scripts", "settings.py")
LOCAL = {
    "typescript": ["typescript", "ts-morph"],
    "javascript": ["typescript", "@babel/parser", "acorn"],
}


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


def local(root, language):
    found = []
    for package in LOCAL.get(language, []):
        d = os.path.join(root, "node_modules", package)
        if os.path.isfile(os.path.join(d, "package.json")):
            found.append(d)
    return found


def settings(root, *args):
    return subprocess.run([sys.executable, SETTINGS_PY, *args, "--repo", root], capture_output=True, text=True)


def chosen(root, language):
    r = settings(root, "get", f"ast.{language}")
    return r.stdout.strip() if r.returncode == 0 else None


def find(root, language):
    found = local(root, language)
    if len(found) == 1:
        print(found[0])
        return
    choice = chosen(root, language)
    if choice:
        print(choice)
        return
    if found:
        print("\n".join(found))
        fail(f"several {language} AST tools are installed; ask the developer which to use, then save it", 2)
    fail(f"no {language} AST tool found; suggest candidates, ask the developer to pick one, then save it", 3)


def main(argv):
    repo = "."
    if "--repo" in argv:
        i = argv.index("--repo")
        repo = argv[i + 1]
        del argv[i:i + 2]
    root = main_checkout(repo)
    if len(argv) == 2 and argv[0] == "find":
        find(root, argv[1].lower())
    elif len(argv) == 3 and argv[0] == "save":
        r = settings(root, "set", f"ast.{argv[1].lower()}", argv[2])
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        sys.exit(r.returncode)
    else:
        fail(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
