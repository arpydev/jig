"""Tests for writing-for-agents' skill_overlap.py."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "writing-for-agents", "scripts"))
import skill_overlap  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "skill_overlap")


class SkillOverlapTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = tmp.name
        with open(os.path.join(self.home, "workflow-packs"), "w") as fh:
            fh.write(os.path.join(FIXTURE, "pack") + "\n")
        os.makedirs(os.path.join(self.home, "plugins"))
        with open(os.path.join(self.home, "plugins", "installed_plugins.json"), "w") as fh:
            json.dump({"version": 2, "plugins": {"toolbox@market": [{"installPath": os.path.join(FIXTURE, "plugin")}]}}, fh)
        os.symlink(os.path.join(FIXTURE, "projects"), os.path.join(self.home, "projects"))
        self.core = os.path.join(FIXTURE, "core")

    def report(self):
        return skill_overlap.report(self.core, self.home)

    def rows(self):
        return {r["name"]: r for r in self.report()["rows"]}

    def pair_names(self):
        return [{p["a"], p["b"]} for p in self.report()["pairs"]]

    def test_one_row_per_skill_across_core_pack_and_plugin(self):
        rows = self.rows()
        self.assertEqual(sorted(rows), ["domain-modeling", "draw", "grill-me", "grilling", "release-train",
                                        "ship-it", "toolbox:pipeline", "toolbox:rollout"])
        self.assertEqual(rows["grilling"]["source"], "core")
        self.assertEqual(rows["release-train"]["source"], "pack pack")
        self.assertEqual(rows["toolbox:pipeline"]["description"],
                         "Run the deploy pipeline. Use when the developer wants a release cut or a production deploy.")
        self.assertEqual(rows["ship-it"]["description"],
                         'Ship a change to production. Use when the developer says "ship it" or wants a release cut.')
        self.assertEqual(rows["grilling"]["lines"], 8)

    def test_loads_and_loaded_by(self):
        rows = self.rows()
        self.assertEqual(rows["grilling"]["loads"], ["domain-modeling"])
        self.assertEqual(rows["ship-it"]["loads"], ["grilling"])
        self.assertEqual(rows["grilling"]["loaded_by"], ["grill-me", "ship-it"])
        self.assertEqual(rows["draw"]["loads"], [])
        self.assertEqual(rows["draw"]["loaded_by"], [])

    def test_alias_is_flagged_and_never_paired(self):
        rows = self.rows()
        self.assertTrue(rows["grill-me"]["alias"])
        # why: ship-it is developer-only and loads grilling too, but does more than load it
        self.assertFalse(rows["ship-it"]["alias"])
        self.assertFalse(rows["grilling"]["alias"])
        self.assertNotIn("grill-me", set().union(*self.pair_names()))

    def test_load_counts_from_skill_calls_and_typed_commands(self):
        rows = self.rows()
        counts = {n: r["used"] for n, r in rows.items()}
        self.assertEqual(counts, {"grilling": 2, "ship-it": 1, "grill-me": 1, "domain-modeling": 1,
                                  "toolbox:pipeline": 1, "toolbox:rollout": 0, "draw": 0,
                                  "release-train": 0})
        self.assertEqual(self.report()["oldest"], "2026-01-05")

    def test_shared_quoted_phrase_ranks_above_word_overlap(self):
        pairs = self.pair_names()
        self.assertEqual(pairs[0], {"ship-it", "release-train"})
        self.assertIn({"ship-it", "toolbox:pipeline"}, pairs)
        self.assertEqual(self.report()["pairs"][0]["phrases"], ["ship it"])
        self.assertNotIn({"draw", "domain-modeling"}, pairs)

    def test_plugin_is_read_only_in_rows_and_pairs(self):
        out = io.StringIO()
        with redirect_stdout(out):
            skill_overlap.main(["--core", self.core, "--claude-home", self.home])
        text = out.getvalue()
        row = next(line for line in text.splitlines() if line.startswith("| toolbox:pipeline "))
        self.assertIn("plugin toolbox, read-only", row)
        pair = next(line for line in text.splitlines() if "toolbox:pipeline" in line and "ship-it" in line
                    and not line.startswith("|"))
        self.assertIn("read-only", pair)
        self.assertNotIn("read-only", next(line for line in text.splitlines() if line.startswith("| ship-it ")))
        self.assertIn("2026-01-05", text)

    def test_two_plugin_skills_are_never_paired(self):
        self.assertNotIn({"toolbox:pipeline", "toolbox:rollout"}, self.pair_names())

    def test_no_transcripts_says_so(self):
        os.unlink(os.path.join(self.home, "projects"))
        out = io.StringIO()
        with redirect_stdout(out):
            skill_overlap.main(["--core", self.core, "--claude-home", self.home])
        self.assertIn("transcripts: none in", out.getvalue())

    def test_default_core_through_an_installed_skill_link_is_the_real_core(self):
        installed = os.path.join(self.home, "skills")
        os.makedirs(installed)
        os.symlink(os.path.join(ROOT, "skills", "writing-for-agents"), os.path.join(installed, "writing-for-agents"))
        script = os.path.join(installed, "writing-for-agents", "scripts", "skill_overlap.py")
        out = subprocess.run([sys.executable, "-I", script, "--claude-home", self.home],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("| tdd | core |", out)


if __name__ == "__main__":
    unittest.main()
