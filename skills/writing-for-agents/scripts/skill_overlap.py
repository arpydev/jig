#!/usr/bin/env python3
"""List every skill the developer has and shortlist the pairs that look like a skill overlap.

Usage: python3 -I skill_overlap.py [--core <dir>] [--claude-home <dir>] [--top <n>]

Reads the core's skills (default: the core this file sits in), each pack listed in
<claude home>/workflow-packs and each plugin in <claude home>/plugins/installed_plugins.json
(<claude home> defaults to $CLAUDE_HOME or ~/.claude). Prints one row per skill: name, source,
SKILL.md line count, the skills it loads, the skills that load it, whether it is an alias skill
and how many times it was loaded in the transcripts under <claude home>/projects (Skill tool
calls and slash commands the developer typed, each counted once even when a resumed session
repeats it), with the date of the oldest transcript read. Then the top pairs most likely to
overlap: pairs quoting the same trigger phrase in their descriptions first, then pairs whose
"Use when…" words (the whole description when it has no "Use when") overlap at or above the
threshold. Alias skills are never paired, nor are two plugin skills. Plugin skills are labelled
read-only: shown, never proposed for change.

An alias skill only the developer can start (disable-model-invocation) and every line of its
body loads another skill. The report proves the facts; the reader decides whether two skills do
the same job. Read-only; prints no transcript content.
"""
import argparse
import glob
import json
import os
import re
import sys

CORE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
THRESHOLD = 0.2
STOPWORDS = set("""a an and any are as asks at be before by can do does for from has have how in
into is it its of on or say says should skill so someone that the their them this to use user
uses wants when whether which who with developer""".split())
QUOTED = re.compile(r"\"([^\"]+)\"|“([^”]+)”|(?<![A-Za-z])'([^']+)'(?![A-Za-z])")
COMMAND = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
LOAD_LINE = [
    re.compile(r"Skill tool\b[^\n]*"),
    re.compile(r"\b[Ll]oads? (?:the )?`[a-z][a-z0-9:-]*`"),
    re.compile(r"`[a-z][a-z0-9:-]*` skill\b"),
]
NAME_IN_LINE = re.compile(r"[\"`“]([a-z][a-z0-9:-]*)[\"`”]")
COMMENT = re.compile(r"<!--.*?-->", re.S)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith(" "):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1].replace('\\"', '"')
            fields[key.strip()] = value
    return fields, text[m.end():]


def skill_dirs(folder):
    if not os.path.isdir(folder):
        return []
    return [(n, os.path.join(folder, n)) for n in sorted(os.listdir(folder))
            if os.path.isfile(os.path.join(folder, n, "SKILL.md"))]


def sources(core, home):
    out = [("core", "", os.path.join(core, "skills"))]
    packs = os.path.join(home, "workflow-packs")
    if os.path.exists(packs):
        for line in read(packs).splitlines():
            if line.strip():
                root = os.path.expanduser(line.strip())
                out.append((f"pack {os.path.basename(root.rstrip('/'))}", "", os.path.join(root, "skills")))
    plugins = os.path.join(home, "plugins", "installed_plugins.json")
    if os.path.exists(plugins):
        for key, installs in sorted(json.loads(read(plugins)).get("plugins", {}).items()):
            name = key.split("@")[0]
            for install in installs[:1]:
                out.append((f"plugin {name}, read-only", f"{name}:", os.path.join(install["installPath"], "skills")))
    return out


def md_texts(skill_dir):
    for d, dirs, names in os.walk(skill_dir):
        dirs[:] = sorted(x for x in dirs if x not in ("upstream", "__pycache__"))
        for n in sorted(names):
            if n.endswith(".md"):
                yield read(os.path.join(d, n))


def loads_in(text, known, prefix):
    found = []
    for pattern in LOAD_LINE:
        for m in pattern.finditer(text):
            for name in NAME_IN_LINE.findall(m.group(0)):
                for candidate in (name, prefix + name):
                    if candidate in known and candidate not in found:
                        found.append(candidate)
    return found


def is_alias(fields, body, loads):
    if fields.get("disable-model-invocation", "").lower() != "true" or not loads:
        return False
    lines = [line for line in COMMENT.sub("", body).splitlines() if line.strip()]
    return all(any(f'"{n}"' in line or f"`{n}`" in line for n in loads) for line in lines)


def transcripts(home):
    return sorted(glob.glob(os.path.join(home, "projects", "**", "*.jsonl"), recursive=True))


def load_counts(paths):
    seen, counts, oldest = set(), {}, None
    for path in paths:
        for raw in read(path).splitlines():
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            stamp = entry.get("timestamp")
            if isinstance(stamp, str) and (oldest is None or stamp < oldest):
                oldest = stamp
            content = (entry.get("message") or {}).get("content") if isinstance(entry.get("message"), dict) else None
            names = []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                        key = ("tool", block.get("id"))
                        if key not in seen:
                            seen.add(key)
                            names.append(str((block.get("input") or {}).get("skill", "")).lstrip("/"))
            if entry.get("type") == "user":
                text = content if isinstance(content, str) else " ".join(
                    b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")
                commands = COMMAND.findall(text)
                key = ("typed", entry.get("uuid") or raw)
                if commands and key not in seen:
                    seen.add(key)
                    names += commands
            for name in names:
                counts[name] = counts.get(name, 0) + 1
    return counts, oldest[:10] if oldest else None


def use_when(description):
    i = description.lower().find("use when")
    return description[i:] if i >= 0 else description


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 1}


def phrases(description):
    return {" ".join(re.findall(r"[a-z0-9]+", "".join(m).lower())) for m in QUOTED.findall(description)}


def report(core, home, top=10):
    rows = []
    for source, prefix, folder in sources(core, home):
        for name, path in skill_dirs(folder):
            text = read(os.path.join(path, "SKILL.md"))
            fields, body = frontmatter(text)
            rows.append({"name": prefix + name, "source": source, "prefix": prefix, "dir": path,
                         "description": fields.get("description", ""), "fields": fields, "body": body,
                         "lines": len(text.splitlines())})
    known = {r["name"] for r in rows}
    for r in rows:
        r["loads"] = []
        for text in md_texts(r["dir"]):
            r["loads"] += [n for n in loads_in(text, known, r["prefix"]) if n != r["name"] and n not in r["loads"]]
        r["alias"] = is_alias(r["fields"], r["body"], r["loads"])
    for r in rows:
        r["loaded_by"] = sorted(o["name"] for o in rows if r["name"] in o["loads"])
    paths = transcripts(home)
    counts, oldest = load_counts(paths)
    for r in rows:
        r["used"] = counts.get(r["name"], 0)
        r["read_only"] = r["source"].endswith("read-only")
    pairs = []
    candidates = [r for r in rows if not r["alias"]]
    for i, a in enumerate(candidates):
        for b in candidates[i + 1:]:
            if a["read_only"] and b["read_only"]:
                continue
            shared = sorted(phrases(a["description"]) & phrases(b["description"]))
            wa, wb = words(use_when(a["description"])), words(use_when(b["description"]))
            overlap = len(wa & wb) / len(wa | wb) if wa | wb else 0.0
            if shared or overlap >= THRESHOLD:
                pairs.append({"a": a["name"], "b": b["name"], "phrases": shared, "overlap": round(overlap, 2),
                              "words": sorted(wa & wb), "read_only": a["read_only"] or b["read_only"]})
    pairs.sort(key=lambda p: (-len(p["phrases"]), -p["overlap"], p["a"], p["b"]))
    for r in rows:
        for k in ("prefix", "dir", "fields", "body"):
            del r[k]
    return {"rows": rows, "pairs": pairs[:top], "oldest": oldest, "transcripts": len(paths),
            "projects": os.path.join(home, "projects")}


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--core", default=CORE)
    ap.add_argument("--claude-home", default=os.environ.get("CLAUDE_HOME") or os.path.expanduser("~/.claude"))
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args(argv)
    if not os.path.isdir(os.path.join(args.core, "skills")):
        sys.exit(f"no skills folder in {args.core}")
    data = report(args.core, args.claude_home, args.top)
    if data["oldest"]:
        print(f"transcripts: {data['transcripts']} read, oldest {data['oldest']}")
    else:
        print(f"transcripts: none in {data['projects']} (load counts are all 0)")
    print()
    print("| Skill | Source | Lines | Loads | Loaded by | Alias | Loaded | Description |")
    print("|---|---|---|---|---|---|---|---|")
    for r in data["rows"]:
        print(f"| {r['name']} | {r['source']} | {r['lines']} | {', '.join(r['loads']) or '-'} | "
              f"{', '.join(r['loaded_by']) or '-'} | {'alias' if r['alias'] else '-'} | {r['used']} | "
              f"{cell(r['description'])} |")
    print()
    print(f"Pairs most likely to overlap (top {args.top}; alias skills and plugin-only pairs left out):")
    if not data["pairs"]:
        print("none: no shared quoted phrase and no \"Use when\" overlap at or above "
              f"{THRESHOLD}")
    for n, p in enumerate(data["pairs"], 1):
        why = []
        if p["phrases"]:
            why.append("both quote " + ", ".join(f'"{x}"' for x in p["phrases"]))
        why.append(f"word overlap {p['overlap']} ({', '.join(p['words']) or 'none'})")
        label = " [plugin, read-only]" if p["read_only"] else ""
        print(f"{n}. {p['a']} ~ {p['b']}{label}: {'; '.join(why)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
