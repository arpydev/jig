import json
import os
import subprocess
import sys
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(CORE, "scripts", "no_regression.py")


class NoRegressionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        return p

    def run_check(self, cfg, approved=None):
        self.write("cfg.json", json.dumps(cfg))
        args = [sys.executable, SCRIPT, os.path.join(self.dir, "cfg.json")]
        if approved is not None:
            args += ["--approved", self.write("ok.json", json.dumps(approved))]
        return subprocess.run(args, capture_output=True, text=True)

    def test_moves_wrapping_and_renames_pass(self):
        self.write("old/skill/SKILL.md", "# Grill\n\nCall the Skill tool for mp-domain-modeling.\nThe product owner approves.\n---\n")
        self.write("new/core/SKILL.md", "# Grill\n")
        self.write("new/pack.md", "Call the skill tool,\nfor `domain-modeling`.\n\nThe developer approves!\n")
        r = self.run_check({"old": ["old"], "new": ["new"], "map": {"mp-domain-modeling": "domain-modeling", "product owner": "developer"}})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("3 old lines: 3 kept", r.stdout)

    def test_a_removed_or_reworded_line_fails_with_its_place(self):
        self.write("old/a.md", "Keep this line.\nThis rule was dropped.\n")
        self.write("new/a.md", "Keep this line.\n")
        r = self.run_check({"old": ["old"], "new": ["new"]})
        self.assertEqual(r.returncode, 1)
        self.assertIn("2: This rule was dropped.", r.stdout)
        self.assertIn("1 not found", r.stdout)

    def test_approved_rewording_passes(self):
        self.write("old/a.md", "This rule was dropped.\n")
        self.write("new/a.md", "Something else.\n")
        r = self.run_check({"old": ["old"], "new": ["new"]}, [{"old": "This rule was dropped.", "why": "agreed"}])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 approved rewordings", r.stdout)

    def test_partial_words_do_not_count(self):
        self.write("old/a.md", "run the tests\n")
        self.write("new/a.md", "rerun the tests\n")
        self.assertEqual(self.run_check({"old": ["old"], "new": ["new"]}).returncode, 1)

    def test_skip_leaves_out_upstream_and_retros(self):
        self.write("old/upstream/SKILL.md", "Matt's own words.\n")
        self.write("old/retros/run.md", "Run notes.\n")
        self.write("old/SKILL.md", "Ours.\n")
        self.write("new/SKILL.md", "Ours.\n")
        r = self.run_check({"old": ["old"], "new": ["new"], "skip": ["upstream/"]})
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
