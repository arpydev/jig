import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(CORE, "skills", "grade-run", "scripts")
SETTINGS = {"version": 1, "committed": True, "tracker": {"kind": "github"}, "checks": "make check",
            "docs": {"glossary": "GLOSSARY.md", "adr": "docs/adr"}, "runData": ".claude/workflow-runs",
            "verifySkill": "verify-demo"}
REPORT = """Gates: G4 criterion 4 not run. G4 again.
C1 3: one low defect at a.ts:3
C2 2: ...
C3 4: ...
C4 3.5: grader wrote a half
C5 3: ...
C6 2: ...
C7 4: ...
Mean: 3.07
Grade: D (gate G4 caps it)
Defects the agent shipped to PR-ready: none
"""


def run(*args, cwd=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=cwd)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        subprocess.run(["git", "init", "-q", self.root], check=True)
        os.makedirs(os.path.join(self.root, ".claude"))
        with open(os.path.join(self.root, ".claude", "workflow.json"), "w") as f:
            json.dump(SETTINGS, f)
        self.report = os.path.join(self.root, "r.md")
        with open(self.report, "w") as f:
            f.write(REPORT)
        self.ledger = os.path.join(self.root, ".claude", "workflow-runs", "grades.md")

    def tearDown(self):
        self.tmp.cleanup()

    def ledger_cmd(self, *args):
        return run(os.path.join(SCRIPTS, "ledger.py"), *args, "--repo", self.root)

    def add(self, run_name="#2", report=None):
        return self.ledger_cmd("add", report or self.report, "--run", run_name, "--mode", "spec-to-pr",
                               "--kind", "counted", "--date", "2026-11-24", "--notes", "a | b")

    def test_add_creates_the_ledger_and_copies_scores_word_for_word(self):
        r = self.add()
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.ledger) as f:
            text = f.read()
        self.assertIn("**Current autonomy level: 0.**", text)
        self.assertIn("## Autonomy ladder", text)
        self.assertIn("| 2026-11-24 | #2 | spec-to-pr | G4 | 3 | 2 | 4 | 3.5 | 3 | 2 | 4 | 3.07 | D |  |  | counted | a \\| b |", text)

    def test_rows_go_in_order_before_level_changes(self):
        self.add("#2")
        self.add("#3")
        with open(self.ledger) as f:
            text = f.read()
        self.assertLess(text.index("| #2 |"), text.index("| #3 |"))
        self.assertLess(text.index("| #3 |"), text.index("## Level changes"))

    def test_incomplete_report_writes_nothing(self):
        bad = os.path.join(self.root, "bad.md")
        with open(bad, "w") as f:
            f.write(REPORT.replace("C6 2: ...\n", "").replace("Mean: 3.07\n", ""))
        r = self.add(report=bad)
        self.assertEqual(r.returncode, 1)
        self.assertIn("C6, Mean", r.stderr)
        self.assertFalse(os.path.exists(self.ledger))

    def test_no_gates_is_none(self):
        clean = os.path.join(self.root, "clean.md")
        with open(clean, "w") as f:
            f.write(REPORT.replace("Gates: G4 criterion 4 not run. G4 again.", "Gates: none"))
        self.add(report=clean)
        with open(self.ledger) as f:
            self.assertIn("| spec-to-pr | none | 3 |", f.read())

    def test_level_reads_the_ledger(self):
        self.assertEqual(self.ledger_cmd("level").stdout.strip(), "0")
        self.add()
        with open(self.ledger) as f:
            text = f.read()
        with open(self.ledger, "w") as f:
            f.write(text.replace("level: 0.", "level: 1."))
        self.assertEqual(self.ledger_cmd("level").stdout.strip(), "1")
        self.assertEqual(self.ledger_cmd("path").stdout.strip(), self.ledger)

    def set_level(self, n):
        with open(self.ledger) as f:
            text = f.read()
        with open(self.ledger, "w") as f:
            f.write(re.sub(r"level: \d+\.", f"level: {n}.", text, count=1))

    def test_gate_follows_the_level_and_some_checkpoints_always_wait(self):
        self.assertEqual(self.ledger_cmd("gate", "merge").stdout.strip(), "wait")
        self.add()
        expected = {0: {"merge": "wait", "pr-ready": "wait"}, 1: {"merge": "go", "layer": "go", "pr-ready": "wait"},
                    2: {"merge": "go", "pr-ready": "go"}}
        for lvl, gates in expected.items():
            self.set_level(lvl)
            for checkpoint, answer in gates.items():
                self.assertEqual(self.ledger_cmd("gate", checkpoint).stdout.strip(), answer, (lvl, checkpoint))
            for never in ("grill", "plan", "outward"):
                self.assertEqual(self.ledger_cmd("gate", never).stdout.strip(), "wait", (lvl, never))
        self.assertNotEqual(self.ledger_cmd("gate", "deploy").returncode, 0)

    def test_add_rewrites_an_old_ladder_from_the_table(self):
        self.add()
        with open(self.ledger) as f:
            text = f.read()
        old = re.sub(r"## Autonomy ladder\n.*?(?=## Grades\n)", "## Autonomy ladder\n\nOld prose.\n\n", text, flags=re.S)
        with open(self.ledger, "w") as f:
            f.write(old)
        self.add("#3")
        with open(self.ledger) as f:
            text = f.read()
        self.assertNotIn("Old prose.", text)
        self.assertIn("| 1 | spec to PR: merge a ticket", text)
        self.assertIn("Always waits for the developer, at every level: the grill;", text)
        self.assertEqual(text.count("## Autonomy ladder"), 1)


class TranscriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        lines = [
            {"type": "user", "message": {"content": "build it"}},
            {"type": "assistant", "message": {"content": [
                {"type": "text", "text": "Running tests"},
                {"type": "tool_use", "name": "Bash", "input": {"command": "x" * 1000}},
                {"type": "tool_use", "name": "SubagentHandback", "input": {"report": "y" * 1000}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "a" * 300 + "MIDDLE" + "b" * 300}]}},
            "not json",
        ]
        self.paths = []
        for n in range(2):
            p = os.path.join(self.tmp.name, f"s{n}.jsonl")
            with open(p, "w") as f:
                f.write("\n".join(l if isinstance(l, str) else json.dumps(l) for l in lines))
            self.paths.append(p)

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, *args):
        return run("-I", os.path.join(SCRIPTS, "transcript.py"), *args).stdout

    def test_developer_sessions(self):
        out = self.render(*self.paths)
        self.assertIn("===== SESSION 1 of 2", out)
        self.assertIn("[DEVELOPER]\nbuild it", out)
        self.assertIn("[CLAUDE]\nRunning tests", out)
        self.assertNotIn("MIDDLE", out)
        self.assertIn("characters cut", out)
        self.assertNotIn("x" * 301, out)
        self.assertIn("y" * 1000, out)

    def test_implementer_runs(self):
        out = self.render(*self.paths, "ORCHESTRATOR")
        self.assertIn("===== RUN 2 of 2", out)
        self.assertIn("[ORCHESTRATOR]\nbuild it", out)
        self.assertNotIn("SESSION", out)

    def test_single_file_has_no_header(self):
        self.assertNotIn("=====", self.render(self.paths[0]))


if __name__ == "__main__":
    unittest.main()
