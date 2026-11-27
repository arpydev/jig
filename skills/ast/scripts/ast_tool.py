#!/usr/bin/env python3
"""Find the AST tool a repository uses for one language.

Usage (run from anywhere inside the repository, or pass --repo):
  ast_tool.py find <language>      print the tool to use and exit 0. Looks first in the repository
                                   (its node_modules), then at `ast.<language>` in the project
                                   settings (a saved path is read from the repository root). Exit 2 with each candidate on its own line when several
                                   are installed and none is chosen; exit 3 when there is none.
                                   Either way the developer picks; save their pick
  ast_tool.py save <language> <tool>
                                   save the developer's pick as `ast.<language>` in the project
                                   settings, so the next `find` returns it
"""
import importlib.util
import os
import sys


def setup_settings():
    """Load setup-workflow's settings.py as a module, so the settings format stays its own business."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                        "setup-workflow", "scripts", "settings.py")
    spec = importlib.util.spec_from_file_location("settings", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


settings = setup_settings()
fail = settings.fail
LOCAL = {
    "typescript": ["typescript", "ts-morph"],
    "javascript": ["typescript", "@babel/parser", "acorn"],
}


def local(root, language):
    found = []
    for package in LOCAL.get(language, []):
        d = os.path.join(root, "node_modules", package)
        if os.path.isfile(os.path.join(d, "package.json")):
            found.append(d)
    return found


def chosen(root, language):
    """The saved ast.<language>, or None when there are no settings or no such key; a broken file fails."""
    if not os.path.exists(os.path.join(root, settings.SETTINGS)):
        return None
    saved = settings.load(root).get("ast", {})
    return saved.get(language) if isinstance(saved, dict) else None


def find(root, language):
    found = local(root, language)
    if len(found) == 1:
        print(found[0])
        return
    choice = chosen(root, language)
    if choice:
        in_repo = os.path.join(root, choice)
        print(in_repo if os.path.exists(in_repo) else choice)
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
    root = settings.main_checkout(repo)
    if len(argv) == 2 and argv[0] == "find":
        find(root, argv[1].lower())
    elif len(argv) == 3 and argv[0] == "save":
        settings.save(root, settings.load(root), f"ast.{argv[1].lower()}", argv[2])
    else:
        fail(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
