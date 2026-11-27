import json
import os
import subprocess
import sys
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AST_TOOL = os.path.join(CORE, "skills", "ast", "scripts", "ast_tool.py")
SETTINGS = {"version": 1, "committed": True, "tracker": {"kind": "github"}, "checks": "pnpm check",
            "docs": {"glossary": "GLOSSARY.md", "adr": "docs/adr"}, "runData": ".claude/workflow-runs",
            "verifySkill": "verify-demo"}


def run(*args):
    return subprocess.run(list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL)


class FixtureRepo(unittest.TestCase):
    """A throwaway git repository standing in for a developer's project."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        run("git", "init", "-q", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, package):
        d = os.path.join(self.root, "node_modules", package)
        os.makedirs(d)
        with open(os.path.join(d, "package.json"), "w") as f:
            json.dump({"name": package, "version": "0.0.0-fixture"}, f)
        return d

    def settings(self, **extra):
        os.makedirs(os.path.join(self.root, ".claude"), exist_ok=True)
        with open(os.path.join(self.root, ".claude", "workflow.json"), "w") as f:
            json.dump(dict(SETTINGS, **extra), f)

    def ast(self, *args):
        return run(sys.executable, AST_TOOL, *args, "--repo", self.root)


class FindTest(FixtureRepo):
    def test_local_typescript_is_returned(self):
        path = self.install("typescript")
        r = self.ast("find", "typescript")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), path)

    def test_settings_tool_is_returned_when_the_repository_has_none(self):
        self.settings(ast={"typescript": "tree-sitter-typescript"})
        r = self.ast("find", "typescript")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "tree-sitter-typescript")

    def test_the_repository_tool_comes_before_the_settings(self):
        path = self.install("typescript")
        self.settings(ast={"typescript": "tree-sitter-typescript"})
        self.assertEqual(self.ast("find", "typescript").stdout.strip(), path)

    def test_two_local_candidates_are_both_listed_and_neither_chosen(self):
        first, second = self.install("typescript"), self.install("ts-morph")
        r = self.ast("find", "typescript")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(sorted(r.stdout.splitlines()), sorted([first, second]))
        self.assertIn("ask the developer", r.stderr)

    def test_a_broken_settings_file_is_reported_not_read_as_nothing_saved(self):
        os.makedirs(os.path.join(self.root, ".claude"))
        with open(os.path.join(self.root, ".claude", "workflow.json"), "w") as f:
            f.write('{"version": 1,')
        r = self.ast("find", "typescript")
        self.assertEqual((r.returncode, r.stdout), (1, ""))
        self.assertIn("is not valid JSON", r.stderr)

    def test_no_candidate_says_so_and_prints_nothing(self):
        r = self.ast("find", "typescript")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout, "")
        self.assertIn("ask the developer", r.stderr)


class SaveTest(FixtureRepo):
    def test_saved_choice_is_found_on_the_next_lookup(self):
        self.install("typescript")
        chosen = self.install("ts-morph")
        self.settings()
        self.assertEqual(self.ast("find", "typescript").returncode, 2)
        r = self.ast("save", "typescript", chosen)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.ast("find", "typescript")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), chosen)

    def test_saving_keeps_the_other_settings(self):
        self.settings(ast={"python": "libcst"})
        self.ast("save", "typescript", "tree-sitter-typescript")
        with open(os.path.join(self.root, ".claude", "workflow.json")) as f:
            saved = json.load(f)
        self.assertEqual(saved, dict(SETTINGS, ast={"python": "libcst", "typescript": "tree-sitter-typescript"}))

    def test_saving_without_settings_fails_and_points_to_setup(self):
        r = self.ast("save", "typescript", "tree-sitter-typescript")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("setup-workflow", r.stderr)


SKILL_LINE_LIMIT = 60


class SkillTest(unittest.TestCase):
    def read(self, *path):
        with open(os.path.join(CORE, *path), encoding="utf-8") as f:
            return f.read()

    def test_skill_says_what_each_suggestion_must_cover_and_stays_short(self):
        text = self.read("skills", "ast", "SKILL.md")
        self.assertLess(len(text.splitlines()), SKILL_LINE_LIMIT)
        for must in ("what it is", "trade-off", "across files", "two to four", "ast_tool.py save"):
            self.assertIn(must, text)

    def test_settings_reference_names_no_npm_command(self):
        text = self.read("skills", "setup-workflow", "references", "settings.md")
        self.assertNotRegex(text, r"(?<![\w-])npm(?![\w-])")
        self.assertRegex(text, r"\bpnpm\b")


if __name__ == "__main__":
    unittest.main()
