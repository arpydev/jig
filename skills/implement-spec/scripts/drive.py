#!/usr/bin/env python3
"""Implementation driver for spec to PR: owns the order of a run's mechanical steps.

The implement-spec skill starts the agents; this script does everything else and says when an
agent is needed. Run from anywhere inside the repository (or pass --repo). <spec> names the run.

  drive.py tickets --check <file>            validate a tickets file (see below)
  drive.py start <spec> --tickets <file> --base <branch> [--branch <name>]
                                             create the integration branch and its worktree
  drive.py next <spec>                       the tickets to start now, or what the run waits on
  drive.py worktree <spec> <ticket>          cut the ticket's branch and worktree from the
                                             integration tip and run the worktreeSetup command
  drive.py started <spec> <ticket> --agent <id>
  drive.py started <spec> --work <label> --agent <id>
                                             record an agent (the grader finds its transcript)
  drive.py report <spec> <ticket> <file>     read the report's last line: PASS, ISSUES or BLOCKED
  drive.py checks <spec> [<ticket>]          run the project's checks in the ticket's worktree
                                             (or the integration worktree); full output saved
  drive.py merge <spec> <ticket> [--approved]
                                             squash-merge a PASS ticket into the integration
                                             branch and run the checks there
  drive.py gate <spec> <checkpoint> --what <text>
                                             go or wait, from the ledger's level; a go at level 1
                                             or above is written to the decision log
  drive.py decide <spec> <what> --why <why>  add a line to the decision log
  drive.py done <spec> <step>                mark a step done
  drive.py skip <spec> <step> --reason <why> mark a step skipped; the reason is required
  drive.py note <spec> <kind> <text>         keep what the next session needs (kind: pr, agreed,
                                             open or ships); `status` prints it
  drive.py status <spec>                     where the run stands: the handoff for a new session
  drive.py cleanup <spec>                    remove the run's worktrees once grading is done

A tickets file is a JSON list of {"id", "title", "blockedBy": [ids], "touches": [paths]}.
"touches" is the ticket's "Likely to touch" list; tickets whose paths overlap run one after the
other, and a ticket with no paths runs alone. `tickets --check` warns about both.

Files, all in <runData>/runs/: <spec>-state.json (the state), <spec>-agents.md (written from the
state), <spec>-decisions.md (the decision log), <spec>-checks-<where>.log (full check output),
and <spec>.md (the friction log the retro reads, started by `start`).
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
SETTINGS = os.path.join(SKILLS, "setup-workflow", "scripts", "settings.py")
LEDGER = os.path.join(SKILLS, "grade-run", "scripts", "ledger.py")
STEPS = {
    "explore": "2: exploration subagent (optional)",
    "tickets": "4-6: implement and merge every ticket",
    "review": "7: review-change, triage and fixes",
    "e2e": "7: the full end-to-end suite on the integration branch",
    "grade": "7b: grade every ticket",
    "pr": "8: PR ready for review, or tickets resolved",
    "cleanup": "9: remove the worktrees",
    "retro": "10: the retro",
}
RESULTS = ("PASS", "ISSUES", "BLOCKED")
MAX_FIXES = 2
TAIL = 40


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def git(*args, cwd, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        fail(f"git {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r


class Run:
    def __init__(self, repo, spec):
        if not re.fullmatch(r"[A-Za-z0-9._-]+", spec):
            fail(f"'{spec}' is not a run name: use letters, digits, dot, dash or underscore")
        self.spec = spec
        self.repo = repo
        self.main = os.path.dirname(os.path.dirname(self.setting_cmd("path")))
        run_data = os.path.expanduser(self.setting("runData"))
        self.runs = os.path.join(run_data if os.path.isabs(run_data) else os.path.join(self.main, run_data), "runs")
        self.state_path = self.file("state.json")
        self.state = None

    def setting_cmd(self, *args, required=True):
        r = subprocess.run([sys.executable, SETTINGS, *args, "--repo", self.repo], capture_output=True, text=True)
        if r.returncode:
            if required:
                fail(r.stderr.strip())
            return None
        return r.stdout.strip()

    def setting(self, key, default=None):
        v = self.setting_cmd("get", key, required=default is None)
        return default if v is None else v

    def file(self, name):
        return os.path.join(self.runs, f"{self.spec}-{name}")

    def load(self):
        if not os.path.exists(self.state_path):
            fail(f"no run {self.spec}: run `drive.py start {self.spec}` first")
        with open(self.state_path) as f:
            self.state = json.load(f)
        session = os.environ.get("CLAUDE_CODE_SESSION_ID")
        if session and session not in self.state["sessions"]:
            self.state["sessions"].append(session)
        return self.state

    def save(self):
        os.makedirs(self.runs, exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        os.replace(tmp, self.state_path)
        self.write_agents()

    def ticket(self, tid):
        t = self.state["tickets"].get(str(tid))
        if not t:
            fail(f"no ticket {tid} in run {self.spec}")
        return t

    def level(self):
        r = subprocess.run([sys.executable, LEDGER, "level", "--repo", self.repo], capture_output=True, text=True)
        if r.returncode:
            fail(r.stderr.strip())
        return int(r.stdout.strip())

    def log(self, what, why):
        os.makedirs(self.runs, exist_ok=True)
        path = self.file("decisions.md")
        new = not os.path.exists(path)
        with open(path, "a") as f:
            if new:
                f.write(f"# {self.spec}: decisions made without asking\n\n")
            f.write(f"- {datetime.datetime.now():%Y-%m-%d %H:%M}: {what}. Why: {why}\n")

    def write_agents(self):
        s = self.state
        lines = [f"# {self.spec}: implementer agents", "",
                 f"Written by `drive.py` from `{self.spec}-state.json`. Integration branch `{s['branch']}`, "
                 f"cut from `{s['base']}` at {s['baseCommit'][:7]}.", "",
                 f"Orchestrating sessions: {', '.join(s['sessions']) or 'not recorded'}. Transcripts are in "
                 "`~/.claude/projects/<project>/<session-id>/subagents/agent-<agent-id>.jsonl`.", "",
                 "| Ticket | Branch | Agent IDs | Base | Status | Merged |", "|---|---|---|---|---|---|"]
        for tid, t in s["tickets"].items():
            lines.append(f"| {tid} {t['title']} | {t.get('branch') or ''} | {', '.join(t['agents'])} | "
                         f"{(t.get('baseCommit') or '')[:7]} | {t['status']} | {(t.get('merged') or '')[:7]} |")
        if s["work"]:
            lines += ["", "Other work (not a ticket):", "", "| Work | Agent ID |", "|---|---|"]
            lines += [f"| {w['label']} | {w['agent']} |" for w in s["work"]]
        with open(self.file("agents.md"), "w") as f:
            f.write("\n".join(lines) + "\n")


# ---------- tickets ----------

def read_tickets(path):
    with open(path) as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            fail(f"{path} is not valid JSON: {e}")
    if not isinstance(raw, list) or not raw:
        fail("a tickets file is a non-empty JSON list")
    problems, tickets = [], {}
    for t in raw:
        tid = str(t.get("id", "")).strip()
        if not tid or not str(t.get("title", "")).strip():
            problems.append(f"every ticket needs an id and a title: {t}")
            continue
        if tid in tickets:
            problems.append(f"ticket {tid} is listed twice")
            continue
        tickets[tid] = {"title": t["title"], "blockedBy": [str(b) for b in t.get("blockedBy", [])],
                        "touches": [os.path.normpath(p) for p in t.get("touches", [])]}
    for tid, t in tickets.items():
        problems += [f"ticket {tid} is blocked by unknown ticket {b}" for b in t["blockedBy"] if b not in tickets]
    if not problems:
        seen, done = set(), set()

        def visit(tid, path):
            if tid in done:
                return
            if tid in seen:
                problems.append(f"blocking cycle: {' -> '.join(path + [tid])}")
                return
            seen.add(tid)
            for b in tickets[tid]["blockedBy"]:
                visit(b, path + [tid])
            done.add(tid)
        for tid in tickets:
            visit(tid, [])
    if problems:
        fail("tickets file not ready:\n- " + "\n- ".join(dict.fromkeys(problems)))
    return tickets


def overlaps(a, b):
    if not a["touches"] or not b["touches"]:
        return True
    return any(p == q or p.startswith(q + os.sep) or q.startswith(p + os.sep) for p in a["touches"] for q in b["touches"])


ACTIVE = ("running", "issues", "pass", "conflict")
WORKING = ("running", "issues", "conflict")  # a PASS waiting for approval holds no implementer
NOTE_KINDS = {"pr": "Draft PR", "agreed": "Agreed with the developer", "open": "Open items",
              "ships": "Ships with"}


def blocked_by_dependency(tickets):
    out, changed = set(), True
    while changed:
        changed = False
        for tid, t in tickets.items():
            if tid not in out and t["status"] == "pending" and any(
                    tickets[b]["status"] == "blocked" or b in out for b in t["blockedBy"]):
                out.add(tid)
                changed = True
    return out


def frontier(state, cap):
    tickets = state["tickets"]
    stuck = blocked_by_dependency(tickets)
    active = [t for t in tickets.values() if t["status"] in ACTIVE]
    working = sum(t["status"] in WORKING for t in tickets.values())
    chosen = []
    for tid, t in tickets.items():
        if working + len(chosen) >= cap:
            break
        if t["status"] != "pending" or tid in stuck:
            continue
        if any(tickets[b]["status"] != "merged" for b in t["blockedBy"]):
            continue
        if any(overlaps(t, o) for o in active + [tickets[c] for c in chosen]):
            continue
        chosen.append(tid)
    return chosen, stuck


def stage_a_over(state):
    """Every ticket is merged, blocked, or waiting behind a blocked ticket."""
    stuck = blocked_by_dependency(state["tickets"])
    return all(t["status"] in ("merged", "blocked") or tid in stuck for tid, t in state["tickets"].items())


def brief(spec):
    return (f"Continue implement-spec for run {spec} at step 7 (review). Run "
            f"`python3 ~/.claude/skills/implement-spec/scripts/drive.py status {spec}` and follow it.")


# ---------- commands ----------

def setup_worktree(run, wt):
    setup = run.setting("worktreeSetup", "")
    if setup:
        r = subprocess.run(setup, shell=True, cwd=wt, capture_output=True, text=True,
                           env=dict(os.environ, MAIN=run.main))
        if r.returncode:
            fail(f"worktreeSetup failed in {wt}:\n{(r.stdout + r.stderr)[-2000:]}")


def start_friction_log(run, sessions):
    path = os.path.join(run.runs, f"{run.spec}.md")
    if os.path.exists(path):
        return
    with open(path, "w") as f:
        f.write(f"# {run.spec}: implement-spec run\n\nStarted: {datetime.date.today().isoformat()}  "
                f"Repo: {os.path.basename(run.main)}\nSessions: {', '.join(sessions)}\nSkill: implement-spec\n\n"
                "## Friction log\n| Step | Type | What happened | Cost |\n|---|---|---|---|\n\n"
                "## Retro outcome\n| Lesson | Fix went to | Change |\n|---|---|---|\n")


def ticket_warnings(tickets, root):
    out = []
    for tid, t in tickets.items():
        if not t["touches"]:
            out.append(f"ticket {tid} has no touches, so it runs alone: map its areas to folders")
        out += [f"ticket {tid} touches {p}, which isn't a path in the repository: map the area to a folder"
                for p in t["touches"] if not os.path.exists(os.path.join(root, p))]
    return out


def cmd_start(run, tickets_file, base, branch):
    if os.path.exists(run.state_path):
        fail(f"run {run.spec} already started; `drive.py status {run.spec}` shows where it stands")
    tickets = read_tickets(tickets_file)
    branch = branch or f"claude/{run.spec}"
    base_commit = git("rev-parse", base, cwd=run.main).stdout.strip()
    if git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", cwd=run.main, check=False).returncode:
        git("branch", branch, base_commit, cwd=run.main)
    wt = os.path.join(run.main, ".claude", "worktrees", f"{run.spec}-integration")
    if not os.path.isdir(wt):
        git("worktree", "add", wt, branch, cwd=run.main)
        setup_worktree(run, wt)
    for t in tickets.values():
        t.update(status="pending", agents=[], fixes=0, branch=None, worktree=None, baseCommit=None, merged=None,
                 report=None)
    run.state = {"spec": run.spec, "base": base, "baseCommit": base_commit, "branch": branch, "worktree": wt,
                 "tickets": tickets, "work": [], "steps": {k: {"state": "pending"} for k in STEPS},
                 "sessions": [s for s in [os.environ.get("CLAUDE_CODE_SESSION_ID")] if s], "firstMerge": None,
                 "notes": []}
    run.save()
    start_friction_log(run, run.state["sessions"])
    print(f"run {run.spec}: integration branch {branch} from {base} at {base_commit[:7]}, worktree {wt}")
    print(f"{len(tickets)} tickets. Next: `drive.py next {run.spec}`")


def cmd_next(run):
    s = run.load()
    cap = int(run.setting("implementers", "1"))
    chosen, stuck = frontier(s, cap)
    for tid in chosen:
        print(f"start {tid}: {s['tickets'][tid]['title']}  (`drive.py worktree {run.spec} {tid}`)")
    for tid in sorted(stuck):
        print(f"blocked by a blocked ticket: {tid}")
    for tid, t in s["tickets"].items():
        if t["status"] == "issues":
            print(f"fix agent needed: {tid} ({t['fixes']} of {MAX_FIXES} fixes used), worktree {t['worktree']}")
        elif t["status"] == "pass":
            print(f"ready to merge: {tid}  (`drive.py merge {run.spec} {tid}`)")
        elif t["status"] == "conflict":
            print(f"merger needed: {tid} conflicts with the integration branch; resolve it in {t['worktree']} "
                  f"by merging {s['branch']} into {t['branch']}, then merge again")
        elif t["status"] == "running":
            print(f"running: {tid}")
    if not chosen and stage_a_over(s):
        blocked = [tid for tid, t in s["tickets"].items() if t["status"] == "blocked"] + sorted(stuck)
        print(f"stage A over: every ticket is merged{' or blocked (' + ', '.join(blocked) + ')' if blocked else ''}.")
        print(f"Start a fresh session for stage B with this brief:\n  {brief(run.spec)}")


def cmd_worktree(run, tid):
    s = run.load()
    t = run.ticket(tid)
    if t["status"] != "pending":
        fail(f"ticket {tid} is {t['status']}, not pending")
    chosen, _ = frontier(s, 10 ** 6)
    if tid not in chosen:
        fail(f"ticket {tid} can't start yet: a blocker isn't merged or its areas overlap a running ticket")
    tip = git("rev-parse", s["branch"], cwd=run.main).stdout.strip()
    branch = f"{s['branch']}-{re.sub(r'[^A-Za-z0-9._-]', '-', tid)}"
    wt = os.path.join(run.main, ".claude", "worktrees", f"{run.spec}-{tid}")
    git("worktree", "add", "-b", branch, wt, tip, cwd=run.main)
    setup_worktree(run, wt)
    t.update(status="running", branch=branch, worktree=wt, baseCommit=tip)
    run.save()
    print(f"{tid}: worktree {wt} on {branch} at {tip[:7]}. Start its implementer there, then "
          f"`drive.py started {run.spec} {tid} --agent <id>`")


def cmd_started(run, tid, work, agent):
    s = run.load()
    if work:
        s["work"].append({"label": work, "agent": agent})
    else:
        t = run.ticket(tid)
        if agent not in t["agents"]:
            t["agents"].append(agent)
    run.save()
    print(f"recorded agent {agent} in {run.file('agents.md')}")


def last_line(path):
    with open(path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
    word = re.sub(r"[`*_.\s]", "", lines[-1]) if lines else ""
    return word if word in RESULTS else None


def cmd_report(run, tid, path):
    s = run.load()
    t = run.ticket(tid)
    result = last_line(path)
    t["report"] = os.path.abspath(path)
    if result == "PASS":
        t["status"] = "pass"
        print(f"{tid}: PASS. Next: `drive.py merge {run.spec} {tid}`")
    elif result == "ISSUES" and t["fixes"] < MAX_FIXES:
        t["fixes"] += 1
        t["status"] = "issues"
        print(f"{tid}: ISSUES. Start a fix agent in {t['worktree']} (fix {t['fixes']} of {MAX_FIXES}), "
              f"record it with `started`, then report again")
    else:
        why = {None: "the report's last line is not PASS, ISSUES or BLOCKED", "ISSUES": f"still ISSUES after {MAX_FIXES} fixes",
               "BLOCKED": "the implementer reported BLOCKED"}[result]
        t["status"] = "blocked"
        t["blockedWhy"] = why
        stuck = blocked_by_dependency(s["tickets"])
        print(f"{tid}: BLOCKED ({why}). Tell the developer; carry on with the other tickets."
              + (f" Also stuck behind it: {', '.join(sorted(stuck))}" if stuck else ""))
    run.save()


def run_checks(run, cwd, where):
    cmd = run.setting("checks")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    os.makedirs(run.runs, exist_ok=True)
    log = run.file(f"checks-{where}.log")
    with open(log, "w") as f:
        f.write(f"$ {cmd}\n(in {cwd})\n\n{r.stdout}{r.stderr}")
    tail = (r.stdout + r.stderr).rstrip().splitlines()[-TAIL:]
    return r.returncode == 0, log, tail


def cmd_checks(run, tid):
    s = run.load()
    cwd, where = (run.ticket(tid)["worktree"], tid) if tid else (s["worktree"], "integration")
    ok, log, tail = run_checks(run, cwd, where)
    print("\n".join(tail))
    print(f"\nchecks {'passed' if ok else 'FAILED'} in {cwd}; full output in {log}")
    sys.exit(0 if ok else 1)


def gate(run, checkpoint, what):
    r = subprocess.run([sys.executable, LEDGER, "gate", checkpoint, "--repo", run.repo], capture_output=True, text=True)
    if r.returncode:
        fail(r.stderr.strip())
    answer = r.stdout.strip()
    if answer == "go":
        run.log(f"passed the {checkpoint} checkpoint without asking: {what}", f"autonomy level {run.level()} allows it")
    return answer


def cmd_merge(run, tid, approved):
    s = run.load()
    t = run.ticket(tid)
    if t["status"] not in ("pass", "conflict"):
        fail(f"ticket {tid} is {t['status']}; only a PASS ticket merges")
    if not approved and gate(run, "merge", f"merge {tid}") != "go":
        fail(f"autonomy level {run.level()}: show the developer ticket {tid}, its report ({t['report']}) and "
             f"`git diff --stat {t['baseCommit'][:7]}...{t['branch']}`, then run "
             f"`drive.py merge {run.spec} {tid} --approved` on their yes", 3)
    wt = s["worktree"]
    if git("status", "--porcelain", cwd=wt).stdout.strip():
        fail(f"the integration worktree {wt} has uncommitted changes; clean it before merging")
    r = git("merge", "--squash", t["branch"], cwd=wt, check=False)
    if r.returncode:
        files = git("diff", "--name-only", "--diff-filter=U", cwd=wt, check=False).stdout.split()
        git("reset", "--hard", "HEAD", cwd=wt)
        t["status"] = "conflict"
        run.save()
        fail(f"conflict: merger needed for {tid} in {', '.join(files) or 'unknown files'}. In {t['worktree']}, merge "
             f"{s['branch']} into {t['branch']} and resolve, then run `drive.py merge {run.spec} {tid}` again", 2)
    if not git("diff", "--cached", "--quiet", cwd=wt, check=False).returncode:
        fail(f"{t['branch']} has nothing to merge into {s['branch']}")
    ref = f"#{tid}" if tid.isdigit() else tid
    git("commit", "-q", "-m", f"{t['title']} ({ref})", cwd=wt)
    ok, log, tail = run_checks(run, wt, "integration")
    if not ok:
        git("reset", "--hard", "HEAD~1", cwd=wt)
        t["status"] = "issues" if t["fixes"] < MAX_FIXES else "blocked"
        if t["status"] == "issues":
            t["fixes"] += 1
        run.save()
        fail("\n".join(tail) + f"\n\nchecks failed after merging {tid}, so the merge was undone (full output in {log}). "
             + (f"Start a fix agent in {t['worktree']}." if t["status"] == "issues" else f"{tid} is now BLOCKED."))
    t["merged"] = git("rev-parse", "HEAD", cwd=wt).stdout.strip()
    t["status"] = "merged"
    t["approvedBy"] = "developer" if approved else "autonomy level"
    first = s["firstMerge"] is None
    s["firstMerge"] = s["firstMerge"] or t["merged"]
    run.save()
    print(f"{tid}: merged into {s['branch']} as {t['merged'][:7]}; checks pass.")
    if first:
        print("First merge: if the tracker closes work through PRs, open the draft PR now (skill step 3).")
    print(f"Next: `drive.py next {run.spec}`")


def cmd_step(run, step, state, reason):
    s = run.load()
    if step not in STEPS:
        fail(f"unknown step {step}: use one of {', '.join(STEPS)}")
    if state == "skipped" and not (reason or "").strip():
        fail("a skipped step needs its reason")
    s["steps"][step] = {"state": state, **({"reason": reason} if reason else {})}
    run.save()
    print(f"{step}: {state}" + (f" ({reason})" if reason else ""))


def cmd_status(run):
    s = run.load()
    run.save()
    level = run.level()
    print(f"Run {run.spec}: integration branch {s['branch']} (worktree {s['worktree']}), autonomy level {level}")
    print("\nTickets:")
    stuck = blocked_by_dependency(s["tickets"])
    for tid, t in s["tickets"].items():
        extra = t.get("blockedWhy") or ("behind a blocked ticket" if tid in stuck else "")
        print(f"  {tid} {t['status']}{': ' + extra if extra else ''} - {t['title']}")
    print("\nSteps (a skipped step keeps its reason for the grader):")
    for k, label in STEPS.items():
        st = s["steps"].get(k, {"state": "pending"})
        print(f"  [{st['state']}] {k}, step {label}" + (f": {st['reason']}" if st.get("reason") else ""))
    notes = s.get("notes", [])
    for kind, label in NOTE_KINDS.items():
        texts = [n["text"] for n in notes if n["kind"] == kind]
        if texts:
            print(f"\n{label}:")
            print("\n".join(f"  - {x}" for x in texts))
    print(f"\nRecords: {run.file('agents.md')}, {run.file('decisions.md')}, friction log {run.spec}.md")
    if stage_a_over(s) and s["steps"]["review"]["state"] == "pending":
        print(f"\nStage A is over. If this session built the tickets, start a fresh one:\n  {brief(run.spec)}")


def cmd_note(run, kind, text):
    s = run.load()
    if kind not in NOTE_KINDS:
        fail(f"unknown note kind {kind}: use one of {', '.join(NOTE_KINDS)}")
    if not text.strip():
        fail("a note needs its text")
    s.setdefault("notes", []).append({"kind": kind, "text": text})
    run.save()
    print(f"noted under {NOTE_KINDS[kind]}; `drive.py status {run.spec}` prints it")


def cmd_cleanup(run):
    s = run.load()
    if s["steps"]["grade"]["state"] == "pending":
        fail("grade every ticket first (or skip the grade step with a reason); branches and worktrees stay until then")
    for path in [t["worktree"] for t in s["tickets"].values() if t["worktree"]] + [s["worktree"]]:
        if os.path.isdir(path):
            r = git("worktree", "remove", path, cwd=run.main, check=False)
            print(f"{'removed' if not r.returncode else 'KEPT (' + r.stderr.strip() + ')'} {path}")
    s["steps"]["cleanup"] = {"state": "done"}
    run.save()
    print("Branches are kept; the state lists each one.")


def main(argv):
    repo = "."
    if "--repo" in argv:
        i = argv.index("--repo")
        repo = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("tickets")
    c.add_argument("--check", required=True)
    c = sub.add_parser("start")
    c.add_argument("spec")
    c.add_argument("--tickets", required=True)
    c.add_argument("--base", required=True)
    c.add_argument("--branch")
    for name in ("next", "status", "cleanup"):
        sub.add_parser(name).add_argument("spec")
    c = sub.add_parser("worktree")
    c.add_argument("spec")
    c.add_argument("ticket")
    c = sub.add_parser("started")
    c.add_argument("spec")
    c.add_argument("ticket", nargs="?")
    c.add_argument("--work")
    c.add_argument("--agent", required=True)
    c = sub.add_parser("report")
    c.add_argument("spec")
    c.add_argument("ticket")
    c.add_argument("file")
    c = sub.add_parser("checks")
    c.add_argument("spec")
    c.add_argument("ticket", nargs="?")
    c = sub.add_parser("merge")
    c.add_argument("spec")
    c.add_argument("ticket")
    c.add_argument("--approved", action="store_true")
    c = sub.add_parser("gate")
    c.add_argument("spec")
    c.add_argument("checkpoint")
    c.add_argument("--what", required=True)
    c = sub.add_parser("decide")
    c.add_argument("spec")
    c.add_argument("what")
    c.add_argument("--why", required=True)
    c = sub.add_parser("done")
    c.add_argument("spec")
    c.add_argument("step")
    c = sub.add_parser("note")
    c.add_argument("spec")
    c.add_argument("kind")
    c.add_argument("text")
    c = sub.add_parser("skip")
    c.add_argument("spec")
    c.add_argument("step")
    c.add_argument("--reason", required=True)
    args = p.parse_args(argv)
    if args.cmd == "tickets":
        tickets = read_tickets(args.check)
        root = git("rev-parse", "--show-toplevel", cwd=repo, check=False).stdout.strip() or repo
        for w in ticket_warnings(tickets, root):
            print(f"warning: {w}")
        print(f"ok: {len(tickets)} tickets")
        return
    run = Run(repo, args.spec)
    if args.cmd == "start":
        cmd_start(run, args.tickets, args.base, args.branch)
    elif args.cmd == "next":
        cmd_next(run)
    elif args.cmd == "worktree":
        cmd_worktree(run, args.ticket)
    elif args.cmd == "started":
        if bool(args.ticket) == bool(args.work):
            fail("give a ticket or --work <label>, not both")
        cmd_started(run, args.ticket, args.work, args.agent)
    elif args.cmd == "report":
        cmd_report(run, args.ticket, args.file)
    elif args.cmd == "checks":
        cmd_checks(run, args.ticket)
    elif args.cmd == "merge":
        cmd_merge(run, args.ticket, args.approved)
    elif args.cmd == "gate":
        run.load()
        print(gate(run, args.checkpoint, args.what))
    elif args.cmd == "decide":
        run.load()
        if not args.why.strip():
            fail("a decision needs its reason")
        run.log(args.what, args.why)
        print(f"logged in {run.file('decisions.md')}")
    elif args.cmd == "done":
        cmd_step(run, args.step, "done", None)
    elif args.cmd == "skip":
        cmd_step(run, args.step, "skipped", args.reason)
    elif args.cmd == "note":
        cmd_note(run, args.kind, args.text)
    elif args.cmd == "status":
        cmd_status(run)
    elif args.cmd == "cleanup":
        cmd_cleanup(run)


if __name__ == "__main__":
    main(sys.argv[1:])
