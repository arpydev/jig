import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVE = os.path.join(CORE, "skills", "implement-spec", "scripts", "drive.py")
FIXTURES = os.path.join(CORE, "tests", "fixtures", "diagram", "run")
SETTINGS = {"version": 1, "committed": True, "tracker": {"kind": "github", "tickets": "gh issue view"},
            "checks": "test ! -e broken", "docs": {"glossary": "GLOSSARY.md", "adr": "docs/adr"},
            "runData": ".claude/workflow-runs", "verifySkill": "verify-demo", "implementers": 2,
            "worktreeSetup": "echo \"$MAIN\" > setup-ran"}
TICKETS = [
    {"id": "1", "title": "Model", "blockedBy": [], "touches": ["src/model"]},
    {"id": "2", "title": "Form", "blockedBy": [], "touches": ["src/form"]},
    {"id": "3", "title": "Form again", "blockedBy": [], "touches": ["src/form/field.py"]},
    {"id": "4", "title": "Page", "blockedBy": ["1"], "touches": ["src/page"]},
]
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
ENV.pop("CLAUDE_CODE_SESSION_ID", None)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=ENV).stdout.strip()


class RunRepo(unittest.TestCase):
    """A throwaway repository with workflow settings, and helpers to drive a run in it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        git("init", "-q", "-b", "main", self.root, cwd=self.root)
        self.write(".claude/workflow.json", json.dumps(SETTINGS))
        self.write(".gitignore", ".claude/worktrees/\n.claude/workflow-runs/\nsetup-ran\n")
        git("add", ".", cwd=self.root)
        git("commit", "-q", "-m", "init", cwd=self.root)
        self.tickets = self.write("tickets.json", json.dumps(TICKETS), commit=False)
        self.runs = os.path.join(self.root, ".claude", "workflow-runs", "runs")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text, base=None, commit=False):
        p = os.path.join(base or self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        if commit:
            git("add", rel, cwd=base or self.root)
            git("commit", "-q", "-m", f"change {rel}", cwd=base or self.root)
        return p

    def drive(self, *args):
        return subprocess.run([sys.executable, DRIVE, *args, "--repo", self.root], capture_output=True, text=True, env=ENV)

    def ok(self, *args):
        r = self.drive(*args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def state(self):
        with open(os.path.join(self.runs, "s1-state.json")) as f:
            return json.load(f)

    def started_ticket(self, tid, text="x = 1\n", rel=None):
        self.ok("worktree", "s1", tid)
        wt = self.state()["tickets"][tid]["worktree"]
        self.write(rel or f"src/t{tid}.py", text, base=wt, commit=True)
        report = self.write(f"report-{tid}.md", "AC 1: test_x passes\n\n**PASS**\n")
        self.ok("report", "s1", tid, report)
        return wt


class DriveTest(RunRepo):
    def test_tickets_file_problems_are_all_reported(self):
        bad = [{"id": "1", "title": "a", "blockedBy": ["2"]}, {"id": "2", "title": "b", "blockedBy": ["1"]},
               {"id": "3", "title": "c", "blockedBy": ["9"]}, {"id": "3", "title": "d"}]
        r = self.drive("tickets", "--check", self.write("bad.json", json.dumps(bad)))
        self.assertEqual(r.returncode, 1)
        self.assertIn("listed twice", r.stderr)
        self.assertIn("unknown ticket 9", r.stderr)
        cyc = [{"id": "1", "title": "a", "blockedBy": ["2"]}, {"id": "2", "title": "b", "blockedBy": ["1"]}]
        self.assertIn("blocking cycle", self.drive("tickets", "--check", self.write("c.json", json.dumps(cyc))).stderr)
        self.assertIn("ok: 4 tickets", self.ok("tickets", "--check", self.tickets))

    def test_next_respects_blockers_overlap_and_the_cap(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.assertEqual(git("rev-parse", "claude/s1", cwd=self.root), git("rev-parse", "main", cwd=self.root))
        out = self.ok("next", "s1")
        self.assertEqual(re.findall(r"^start (\d+)", out, re.M), ["1", "2"])
        self.ok("worktree", "s1", "2")
        out = self.ok("next", "s1")
        self.assertEqual(re.findall(r"^start (\d+)", out, re.M), ["1"])
        self.assertNotEqual(self.drive("worktree", "s1", "3").returncode, 0)
        self.assertNotEqual(self.drive("worktree", "s1", "4").returncode, 0)

    def test_a_ticket_with_no_areas_runs_alone(self):
        tickets = [{"id": "1", "title": "a"}, {"id": "2", "title": "b", "touches": ["x"]}]
        self.ok("start", "s1", "--tickets", self.write("t.json", json.dumps(tickets)), "--base", "main")
        self.assertEqual(re.findall(r"^start (\d+)", self.ok("next", "s1"), re.M), ["1"])

    def test_worktree_is_cut_from_the_integration_tip_and_set_up(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.ok("worktree", "s1", "1")
        t = self.state()["tickets"]["1"]
        with open(os.path.join(t["worktree"], "setup-ran")) as f:
            self.assertEqual(f.read().strip(), self.root)
        self.assertEqual(git("rev-parse", "HEAD", cwd=t["worktree"]), git("rev-parse", "claude/s1", cwd=self.root))
        self.ok("started", "s1", "1", "--agent", "abc123")
        self.ok("started", "s1", "--work", "Review fixes", "--agent", "def456")
        with open(os.path.join(self.runs, "s1-agents.md")) as f:
            agents = f.read()
        self.assertIn("| 1 Model | claude/s1-1 | abc123 |", agents)
        self.assertIn("| Review fixes | def456 |", agents)

    def test_level_0_merge_waits_for_approval_then_squashes(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        wt = self.started_ticket("1")
        self.write("src/t1b.py", "y = 2\n", base=wt, commit=True)
        r = self.drive("merge", "s1", "1")
        self.assertEqual(r.returncode, 3)
        self.assertIn("--approved", r.stderr)
        self.assertEqual(self.state()["tickets"]["1"]["status"], "pass")
        self.ok("merge", "s1", "1", "--approved")
        log = git("log", "--format=%s", "claude/s1", cwd=self.root).splitlines()
        self.assertEqual(log, ["Model (#1)", "init"])
        t = self.state()["tickets"]["1"]
        self.assertEqual(t["merged"], git("rev-parse", "claude/s1", cwd=self.root))
        self.assertIn("start 4", self.ok("next", "s1"))
        self.assertFalse(os.path.exists(os.path.join(self.runs, "s1-decisions.md")))

    def test_level_1_merges_without_asking_and_logs_the_decision(self):
        self.write(".claude/workflow-runs/grades.md", "**Current autonomy level: 1.**\n")
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.started_ticket("1")
        self.ok("merge", "s1", "1")
        with open(os.path.join(self.runs, "s1-decisions.md")) as f:
            self.assertIn("passed the merge checkpoint without asking: merge 1. Why: autonomy level 1", f.read())
        self.assertEqual(self.ok("gate", "s1", "pr-ready", "--what", "x").strip(), "wait")

    def test_issues_twice_then_blocked_and_dependents_leave_the_frontier(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.ok("worktree", "s1", "1")
        issues = self.write("r.md", "AC 2 unmet\nISSUES\n")
        self.ok("report", "s1", "1", issues)
        self.ok("report", "s1", "1", issues)
        self.assertEqual(self.state()["tickets"]["1"]["status"], "issues")
        self.ok("report", "s1", "1", issues)
        self.assertEqual(self.state()["tickets"]["1"]["status"], "blocked")
        out = self.ok("next", "s1")
        self.assertIn("blocked by a blocked ticket: 4", out)
        self.assertNotIn("start 4", out)

    def test_a_report_without_a_result_line_is_blocked(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.ok("worktree", "s1", "2")
        self.ok("report", "s1", "2", self.write("r.md", "All done, I think.\n"))
        self.assertIn("not PASS, ISSUES or BLOCKED", self.state()["tickets"]["2"]["blockedWhy"])

    def test_a_conflict_asks_for_a_merger_and_leaves_the_integration_branch_clean(self):
        tickets = [{"id": "1", "title": "a", "touches": ["a"]}, {"id": "2", "title": "b", "touches": ["b"]}]
        self.ok("start", "s1", "--tickets", self.write("t.json", json.dumps(tickets)), "--base", "main")
        self.started_ticket("1", "one\n", rel="shared.txt")
        self.started_ticket("2", "two\n", rel="shared.txt")
        self.ok("merge", "s1", "1", "--approved")
        r = self.drive("merge", "s1", "2", "--approved")
        self.assertEqual(r.returncode, 2)
        self.assertIn("merger needed", r.stderr)
        integ = self.state()["worktree"]
        self.assertEqual(git("status", "--porcelain", cwd=integ), "")
        self.assertIn("merger needed: 2", self.ok("next", "s1"))

    def test_failing_checks_after_a_merge_undo_it(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.started_ticket("1", "bad\n", rel="broken")
        before = git("rev-parse", "claude/s1", cwd=self.root)
        r = self.drive("merge", "s1", "1", "--approved")
        self.assertEqual(r.returncode, 1)
        self.assertIn("merge was undone", r.stderr)
        self.assertEqual(git("rev-parse", "claude/s1", cwd=self.root), before)
        self.assertEqual(self.state()["tickets"]["1"]["status"], "issues")
        self.assertTrue(os.path.exists(os.path.join(self.runs, "s1-checks-integration.log")))

    def test_skips_need_a_reason_and_status_lists_every_step(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.assertNotEqual(self.drive("skip", "s1", "explore", "--reason", " ").returncode, 0)
        self.ok("skip", "s1", "explore", "--reason", "tickets name the code")
        self.ok("decide", "s1", "kept the auto-match", "--why", "the developer asked")
        out = self.ok("status", "s1")
        self.assertIn("[skipped] explore, step 2: exploration subagent (optional): tickets name the code", out)
        self.assertIn("[pending] grade", out)
        self.assertIn("[pending] retro, step 10: the retro", out)
        self.assertNotEqual(self.drive("cleanup", "s1").returncode, 0)

    def test_stage_a_ends_when_every_ticket_is_merged_or_blocked(self):
        tickets = [{"id": "1", "title": "a", "touches": ["a"]}, {"id": "2", "title": "b", "blockedBy": ["1"]}]
        self.ok("start", "s1", "--tickets", self.write("t.json", json.dumps(tickets)), "--base", "main")
        self.assertNotIn("stage A over", self.ok("next", "s1"))
        self.ok("worktree", "s1", "1")
        self.ok("report", "s1", "1", self.write("r.md", "BLOCKED\n"))
        out = self.ok("next", "s1")
        self.assertIn("stage A over", out)
        self.assertIn("fresh session", out)

    def test_cleanup_removes_worktrees_and_keeps_branches(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        wt = self.started_ticket("1")
        self.ok("merge", "s1", "1", "--approved")
        self.ok("done", "s1", "grade")
        os.remove(os.path.join(wt, "setup-ran"))
        self.ok("cleanup", "s1")
        self.assertFalse(os.path.isdir(wt))
        self.assertTrue(git("branch", "--list", "claude/s1-1", cwd=self.root))



    # Fixes from the step 7 comparison.

    def test_start_sets_up_the_integration_worktree(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        with open(os.path.join(self.state()["worktree"], "setup-ran")) as f:
            self.assertEqual(f.read().strip(), self.root)

    def test_a_pass_waiting_for_approval_holds_no_implementer_slot(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.started_ticket("1")
        self.started_ticket("2", rel="src/form/a.py")
        self.assertEqual([t["status"] for t in self.state()["tickets"].values()][:2], ["pass", "pass"])
        # Both slots are free, but 3 overlaps 2 (still unmerged) and 4 waits for 1.
        self.assertEqual(re.findall(r"^start (\d+)", self.ok("next", "s1"), re.M), [])
        self.ok("merge", "s1", "1", "--approved")
        self.assertEqual(re.findall(r"^start (\d+)", self.ok("next", "s1"), re.M), ["4"])

    def test_tickets_check_warns_about_missing_and_empty_touches(self):
        self.write("src/model/m.py", "", commit=True)
        tickets = [{"id": "1", "title": "a", "touches": ["src/model"]}, {"id": "2", "title": "b"},
                   {"id": "3", "title": "c", "touches": ["the recipe form"]}]
        out = self.ok("tickets", "--check", self.write("w.json", json.dumps(tickets)))
        self.assertNotIn("ticket 1", out)
        self.assertIn("warning: ticket 2 has no touches", out)
        self.assertIn("warning: ticket 3 touches the recipe form, which isn't a path", out)
        self.assertIn("ok: 3 tickets", out)

    def test_start_begins_the_friction_log_once(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        path = os.path.join(self.runs, "s1.md")
        with open(path) as f:
            log = f.read()
        self.assertIn("Skill: implement-spec", log)
        self.assertIn("## Friction log", log)
        self.assertIn("## Retro outcome", log)

    def test_notes_reach_status_by_kind(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.ok("note", "s1", "pr", "https://example.test/pr/1")
        self.ok("note", "s1", "ships", "run the migration in production")
        self.assertNotEqual(self.drive("note", "s1", "lunch", "x").returncode, 0)
        self.assertNotEqual(self.drive("note", "s1", "open", " ").returncode, 0)
        out = self.ok("status", "s1")
        self.assertIn("Draft PR:\n  - https://example.test/pr/1", out)
        self.assertIn("Ships with:\n  - run the migration in production", out)
        self.assertNotIn("Open items", out)


class DiagramTest(RunRepo):
    """Plan and proof diagrams: graph files in the run's data folder, and a mismatch stops the merge."""

    def setUp(self):
        if not shutil.which("node"):
            self.skipTest("node is not installed: the diagram scripts need Node")
        super().setUp()

    def graph(self, name):
        return os.path.join(FIXTURES, name)

    def plan(self, tid="1"):
        return self.ok("diagram", "s1", "plan", self.graph("current.json"), self.graph("expected.json"),
                       "--ticket", tid)

    def proof(self, after, tid="1"):
        return self.drive("diagram", "s1", "proof", self.graph("current.json"), self.graph(after),
                          "--ticket", tid, "--kind", "call-tree")

    def test_graph_files_are_written_under_the_run_data_folder(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.plan()
        self.assertEqual(self.proof("after-match.json").returncode, 0)
        self.assertEqual(sorted(f for f in os.listdir(self.runs) if f.startswith("s1-1-")),
                         ["s1-1-plan.json", "s1-1-pr.md", "s1-1-proof.json"])
        self.assertEqual(git("status", "--porcelain", "--untracked-files=all", cwd=self.root), "?? tickets.json")

    def test_a_mismatch_stops_the_merge_at_level_2_until_the_proof_matches(self):
        self.write(".claude/workflow-runs/grades.md", "**Current autonomy level: 2.**\n")
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        wt = self.started_ticket("1")
        self.plan()
        before = git("rev-parse", "claude/s1", cwd=self.root)
        self.assertNotEqual(self.drive("merge", "s1", "1").returncode, 0, "no proof yet")
        r = self.proof("after-mismatch.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("changed edge Start -> Finish: mark removed, now unchanged", r.stdout)
        for args in (("merge", "s1", "1"), ("merge", "s1", "1", "--approved"), ("checks", "s1", "1")):
            r = self.drive(*args)
            self.assertEqual(r.returncode, 1, args)
            self.assertIn("proof diagram doesn't match the plan diagram", r.stderr + r.stdout)
        self.assertEqual(git("rev-parse", "claude/s1", cwd=self.root), before)
        self.assertEqual(self.proof("after-match.json").returncode, 0)
        self.ok("checks", "s1", "1")
        self.ok("merge", "s1", "1")
        self.assertNotEqual(git("rev-parse", "claude/s1", cwd=self.root), before)
        self.assertTrue(os.path.isdir(wt))

    def test_a_new_plan_drops_the_old_proof(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.started_ticket("1")
        self.plan()
        self.assertEqual(self.proof("after-match.json").returncode, 0)
        self.plan()
        self.assertNotEqual(self.drive("merge", "s1", "1", "--approved").returncode, 0)

    def test_a_ticket_without_a_plan_diagram_merges_as_before(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.started_ticket("1")
        self.ok("merge", "s1", "1", "--approved")

    def test_a_match_writes_the_pr_section_from_the_template(self):
        self.ok("start", "s1", "--tickets", self.tickets, "--base", "main")
        self.plan()
        out = self.proof("after-match.json").stdout
        line = "Proof diagram matched the plan diagram (call-tree, 1 node added, 2 edges added, 1 group removed, " \
               "1 node removed, 2 edges removed)"
        self.assertIn(line, out)
        with open(os.path.join(self.runs, "s1-1-pr.md")) as f:
            pr = f.read()
        self.assertTrue(pr.startswith(line + "\n"), pr)
        details = re.search(r"<details>\n<summary>[^<]+</summary>\n\n```mermaid\n(.*?)```\n\n</details>", pr, re.S)
        self.assertIsNotNone(details, pr)
        self.assertIn('n1["Check"]', details.group(1))
        self.assertIn("class n1 added", details.group(1))


class PrBodyTemplateTest(unittest.TestCase):
    """The PR body template holds the result line and the merged diagram in a collapsed section."""

    def test_template_has_the_result_line_and_a_collapsed_mermaid_block(self):
        with open(os.path.join(CORE, "skills", "implement-spec", "references", "pr-body.md")) as f:
            template = f.read()
        self.assertRegex(template, r"\{result\}\n\n<details>\n<summary>[^<]+</summary>\n\n\{mermaid\}\n\n</details>")


if __name__ == "__main__":
    unittest.main()
