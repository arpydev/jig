"""Tests for skills/knowledge-map/scripts/knowledge.py, run against a throwaway git repository."""
import datetime
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(CORE, "skills", "knowledge-map", "scripts", "knowledge.py")
spec = importlib.util.spec_from_file_location("knowledge", SCRIPT)
knowledge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knowledge)

TODAY = datetime.date(2026, 6, 1)


class KnowledgeMap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "shop")
        os.makedirs(os.path.join(self.repo, "src", "baskets"))
        os.environ["KNOWLEDGE_DIR"] = os.path.join(self.tmp.name, "knowledge")
        self.git("init", "-q")
        self.commit("first", "2026-01-01")

    def tearDown(self):
        os.environ.pop("KNOWLEDGE_DIR", None)
        self.tmp.cleanup()

    def git(self, *args, date=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        if date:
            env.update(GIT_AUTHOR_DATE=f"{date}T12:00:00", GIT_COMMITTER_DATE=f"{date}T12:00:00")
        subprocess.run(["git", "-C", self.repo, *args], check=True, env=env, capture_output=True)

    def commit(self, message, date):
        with open(os.path.join(self.repo, "src", "baskets", "basket.ts"), "a") as f:
            f.write(message + "\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, date=date)

    def record(self, area, level, date, paths="src/baskets/"):
        with redirect_stdout(io.StringIO()):
            knowledge.record(self.repo, area, level, "explained the basket total", paths, date)

    def status(self, *paths):
        out = io.StringIO()
        with redirect_stdout(out):
            knowledge.status(self.repo, list(paths), TODAY)
        return out.getvalue()

    def area(self, name="Baskets"):
        return knowledge.load(knowledge.map_path(self.repo))[name]

    def test_map_is_named_after_the_main_checkout_and_lives_outside_it(self):
        path = knowledge.map_path(self.repo)
        self.assertEqual(os.path.basename(path), "shop.md")
        self.assertFalse(path.startswith(self.repo))

    def test_record_round_trips_and_keeps_every_evidence_line(self):
        self.record("Baskets", "followed it", "2026-05-01")
        self.record("Baskets", "can explain", "2026-05-20", paths=None)
        area = self.area()
        self.assertEqual(area["level"], "can explain")
        self.assertEqual(area["paths"], ["src/baskets/"])
        self.assertEqual([d for d, _ in area["evidence"]], ["2026-05-01", "2026-05-20"])

    def test_new_area_needs_paths_and_level_must_be_known(self):
        with self.assertRaises(SystemExit):
            knowledge.record(self.repo, "Baskets", "can explain", "x", None, "2026-05-01")
        with self.assertRaises(SystemExit):
            knowledge.record(self.repo, "Baskets", "expert", "x", "src/", "2026-05-01")

    def test_known_area_with_fresh_evidence_needs_no_explaining(self):
        self.record("Baskets", "can explain", "2026-05-20")
        self.assertIn("knows it", self.status("src/baskets/basket.ts"))

    def test_low_level_means_explain_first(self):
        self.record("Baskets", "followed it", "2026-05-20")
        self.assertIn("explain and ask first", self.status("src/baskets/basket.ts"))

    def test_old_evidence_is_due_a_recheck_even_at_can_teach(self):
        self.record("Baskets", "can teach", "2026-01-15")
        line = self.status("src/baskets/basket.ts")
        self.assertIn("explain and ask first", line)
        self.assertIn("evidence is 137 days old", line)

    def test_many_commits_since_evidence_is_due_a_recheck(self):
        self.record("Baskets", "can explain", "2026-05-01")
        for i in range(knowledge.STALE_COMMITS):
            self.commit(f"change {i}", "2026-05-10")
        self.assertIn(f"{knowledge.STALE_COMMITS} commits since", self.status())

    def test_paths_no_area_covers_are_listed_as_new(self):
        self.record("Baskets", "can explain", "2026-05-20")
        out = self.status("src/payments/card.ts")
        self.assertIn("no area | src/payments/card.ts", out)
        self.assertNotIn("Baskets |", out)

    def test_warnings_name_areas_the_text_mentions_loosely(self):
        self.record("Baskets", "followed it", "2026-05-20")
        self.record("Check-ins", "can explain", "2026-05-20", paths="src/check-ins/")
        self.assertEqual(knowledge.warnings("Test notes: add a basket and pay", self.repo, TODAY),
                         ["Baskets (level is followed it)"])
        self.assertEqual(knowledge.warnings("Fixes the check-in reminder", self.repo, TODAY), [])
        self.assertEqual(knowledge.warnings("Touches src/baskets/total.ts", self.repo, TODAY),
                         ["Baskets (level is followed it)"])


if __name__ == "__main__":
    unittest.main()
