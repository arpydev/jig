"""Outbound check (loaded by outbound-guard): warn when outgoing text names an area the developer doesn't yet know well.

Reads the knowledge map through the knowledge-map skill's script. It only warns: the developer
still approves the write in the same prompt.
"""
import datetime
import importlib.util
import os

SCRIPT_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                 "skills", "knowledge-map", "scripts", "knowledge.py"),
    os.path.expanduser("~/.claude/skills/knowledge-map/scripts/knowledge.py"),
]


def load_script():
    for path in SCRIPT_CANDIDATES:
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("knowledge_map", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


def warn(text, cwd):
    knowledge = load_script()
    if not knowledge or not cwd:
        return []
    try:
        if not os.path.exists(knowledge.map_path(cwd)):
            return []
        areas = knowledge.warnings(text, cwd, datetime.date.today())
    except SystemExit:  # why: knowledge.py exits outside a git repository
        return []
    if not areas:
        return []
    return [f"Knowledge map: this names {', '.join(areas)}. Could you explain and defend it without Claude?"]
