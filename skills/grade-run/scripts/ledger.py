#!/usr/bin/env python3
"""The project's grade ledger: <runData>/grades.md.

Usage (from inside the repository, or with --repo):
  ledger.py add <grade report> --run <run> --mode interactive|spec-to-pr --kind calibration|counted
                [--dev <letter>] [--notes <text>] [--date YYYY-MM-DD]
      Copy the grader's gates, scores, mean and grade into a new row, word for word.
      Creates the ledger, with autonomy level 0 and the ladder, if there is none.
      Exits 1, writing nothing, if the report lacks any of Gates, C1 to C7, Mean or Grade,
      or a score isn't a whole number 0 to 4.
  ledger.py level                 print the current autonomy level
  ledger.py gate <checkpoint>     print go if the current level passes the checkpoint without
                                  waiting for the developer, otherwise wait
  ledger.py path                  print the ledger's path

The ladder is CHECKPOINTS below. The ledger's "Autonomy ladder" section is written from it,
and `add` rewrites that section each time, so the text never drifts from the code.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

SETTINGS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                        "setup-workflow", "scripts", "settings.py")
COLUMNS = ["Date", "Run", "Mode", "Gates", "C1", "C2", "C3", "C4", "C5", "C6", "C7",
           "Mean", "Grader", "Dev", "Escaped", "Kind", "Notes"]
MODES = ["interactive", "spec-to-pr"]
KINDS = ["calibration", "counted"]
LEVEL = re.compile(r"\*\*Current autonomy level: (\d+)\.\*\*")

# checkpoint: (lowest level that passes it without waiting, or None for never; what it is)
CHECKPOINTS = {
    "grill": (None, "the grill"),
    "plan": (None, "the plan (in spec to PR, the spec and its tickets)"),
    "merge": (1, "spec to PR: merge a ticket into the integration branch"),
    "layer": (1, "interactive: build a layer, run its checks and carry on to the next"),
    "pr-ready": (2, "mark the PR ready for review at the end of the run"),
    "outward": (None, "an irreversible or outward action: a push, merging into main, closing or editing an issue, "
                      "a deploy outside the developer's own stack"),
}
TO_REACH = {
    0: "Starting level",
    1: "Calibration done; 10 graded runs since; those 10 average B or better; no gate hit; no medium or high "
       "escaped defect; the developer's blind grade within one letter of the grader's on 8 of the 10 that had one "
       "(all of them, if fewer than 10 had one)",
    2: "Agreed with the developer at the time",
}


def ladder():
    """The ledger's "Autonomy ladder" section, written from CHECKPOINTS."""
    rows = []
    for lvl in sorted(TO_REACH):
        passes = [what for lowest, what in CHECKPOINTS.values() if lowest is not None and lowest <= lvl]
        rows.append(f"| {lvl} | {'; '.join(passes) or 'nothing'} | {TO_REACH[lvl]} |")
    never = "; ".join(what for lowest, what in CHECKPOINTS.values() if lowest is None)
    return ("## Autonomy ladder\n\n"
            "Written by `ledger.py` from its `CHECKPOINTS` table; `ledger.py gate <checkpoint>` answers from the same table.\n\n"
            "| Level | What may run without waiting | To reach it |\n|---|---|---|\n" + "\n".join(rows) + "\n\n"
            f"Always waits for the developer, at every level: {never}.\n\n"
            "Any gate hit, or an escaped high-severity defect, drops one level at once.\n\n")

HEADER = """# Run grades

**Current autonomy level: 0.** The developer decides every change of level; each one is noted under "Level changes".

Written by `grade-run`'s `scripts/ledger.py`. Scores come from the grader word for word; Claude never edits them. "Mode" is interactive (the developer approves each checkpoint) or spec-to-pr (implementer subagents). "Dev" is the developer's blind grade (blank when none was due). "Escaped" is filled in later, from defects found after the work was called ready.

{ladder}## Grades

| {cols} |
|{seps}|

## Level changes

| Date | From | To | Why |
|---|---|---|---|
""".replace("{cols}", " | ".join(COLUMNS)).replace("{seps}", "|".join(["---"] * len(COLUMNS)))


def header():
    return HEADER.replace("{ladder}", ladder())


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def ledger_path(repo):
    r = subprocess.run([sys.executable, SETTINGS, "get", "runData", "--repo", repo], capture_output=True, text=True)
    if r.returncode:
        fail(r.stderr.strip() or "no runData in the project settings")
    run_data = os.path.expanduser(r.stdout.strip())
    if not os.path.isabs(run_data):
        root = os.path.dirname(os.path.dirname(subprocess.run(
            [sys.executable, SETTINGS, "path", "--repo", repo], capture_output=True, text=True, check=True).stdout.strip()))
        run_data = os.path.join(root, run_data)
    return os.path.join(run_data, "grades.md")


def parse(report):
    """The grader's values as written. Missing lines are reported, not guessed.

    The grade file also holds the prompt as sent, whose placeholder lines would match first,
    so only the text after "## Grader report" is read when that heading is there."""
    report = report.split("\n## Grader report", 1)[-1]
    found, missing = {}, []
    patterns = {"Gates": r"^Gates:\s*(.+)$"}
    patterns.update({f"C{i}": rf"^C{i}\s+([0-9.]+)\s*:" for i in range(1, 8)})
    patterns.update({"Mean": r"^Mean:\s*(\S+)", "Grade": r"^Grade:\s*([A-F])\b"})
    for key, pattern in patterns.items():
        m = re.search(pattern, report, re.MULTILINE)
        if m:
            found[key] = m.group(1).strip()
        else:
            missing.append(key)
    if missing:
        fail(f"grade report lacks: {', '.join(missing)}")
    for i in range(1, 8):
        if found[f"C{i}"] not in {"0", "1", "2", "3", "4"}:
            fail(f"C{i} is {found[f'C{i}']}; the rubric needs a whole number 0 to 4, so ask the grader again")
    gates = found["Gates"]
    found["Gates"] = "none" if gates.lower().startswith("none") else ", ".join(dict.fromkeys(re.findall(r"\bG[1-9]\b", gates))) or gates
    return found


def cell(text):
    return (text or "").replace("|", "\\|").replace("\n", " ")


def add(args):
    with open(args.report, encoding="utf-8") as f:
        g = parse(f.read())
    path = ledger_path(args.repo)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(header())
    with open(path) as f:
        text = f.read()
    text = re.sub(r"## Autonomy ladder\n.*?(?=## Grades\n)", lambda _: ladder(), text, count=1, flags=re.S)
    marker = "\n## Level changes"
    if marker not in text:
        fail(f"{path} has no '## Level changes' section; fix the ledger by hand")
    values = [args.date or datetime.date.today().isoformat(), args.run, args.mode, g["Gates"]]
    values += [g[f"C{i}"] for i in range(1, 8)]
    values += [g["Mean"], g["Grade"], args.dev or "", "", args.kind, args.notes or ""]
    row = "| " + " | ".join(cell(v) for v in values) + " |\n"
    head, tail = text.split(marker, 1)
    with open(path, "w") as f:
        f.write(head.rstrip("\n") + "\n" + row + marker + tail)
    print(f"added {args.run} to {path}: {g['Grade']} (mean {g['Mean']}, gates {g['Gates']})")


def current_level(repo):
    path = ledger_path(repo)
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        m = LEVEL.search(f.read())
    if not m:
        fail(f"{path} has no '**Current autonomy level: N.**' line")
    return int(m.group(1))


def gate(repo, checkpoint):
    lowest = CHECKPOINTS[checkpoint][0]
    return "go" if lowest is not None and current_level(repo) >= lowest else "wait"


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("report")
    a.add_argument("--run", required=True)
    a.add_argument("--mode", required=True, choices=MODES)
    a.add_argument("--kind", required=True, choices=KINDS)
    a.add_argument("--dev")
    a.add_argument("--notes")
    a.add_argument("--date")
    a.add_argument("--repo", default=argparse.SUPPRESS)
    for name in ("level", "path"):
        sub.add_parser(name).add_argument("--repo", default=argparse.SUPPRESS)
    g = sub.add_parser("gate")
    g.add_argument("checkpoint", choices=list(CHECKPOINTS))
    g.add_argument("--repo", default=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.cmd == "add":
        add(args)
    elif args.cmd == "level":
        print(current_level(args.repo))
    elif args.cmd == "gate":
        print(gate(args.repo, args.checkpoint))
    else:
        print(ledger_path(args.repo))


if __name__ == "__main__":
    main(sys.argv[1:])
