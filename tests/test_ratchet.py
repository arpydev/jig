import json
import os
import subprocess
import sys
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATCHET = os.path.join(CORE, "skills", "setup-workflow", "scripts", "ratchet.py")
RULE = "grep -rn --include=*.py TODO src"


class RatchetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.write("src/a.py", "x = 1  # TODO\ny = 2  # TODO\n")
        self.write("src/b.py", "z = 3  # TODO\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)

    def ratchet(self, *args, cwd=None):
        return subprocess.run([sys.executable, RATCHET, *args], capture_output=True, text=True,
                              cwd=cwd or os.path.join(self.root, "src"))

    def baseline(self):
        with open(os.path.join(self.root, ".ratchet", "todo.json")) as f:
            return json.load(f)["baseline"]

    def add(self):
        r = self.ratchet("add", "todo", "--command", RULE, "--reason", "say it in an issue")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_add_records_todays_breaches_per_file(self):
        self.add()
        self.assertEqual(self.baseline(), {"src/a.py": 2, "src/b.py": 1})
        self.assertEqual(self.ratchet("check").stdout.strip(), "ok")
        self.assertNotEqual(self.ratchet("add", "todo", "--command", RULE, "--reason", "again").returncode, 0)

    def test_a_new_breach_fails_even_when_another_file_improved(self):
        self.add()
        self.write("src/a.py", "x = 1\n")
        self.write("src/c.py", "w = 4  # TODO\n")
        r = self.ratchet("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("src/c.py: 1 (allowed 0)", r.stdout)
        self.assertNotEqual(self.ratchet("lower").returncode, 0)
        self.assertEqual(self.baseline(), {"src/a.py": 2, "src/b.py": 1})

    def test_fixed_breaches_fail_until_lowered_and_lower_never_raises(self):
        self.add()
        self.write("src/a.py", "x = 1  # TODO\n")
        self.write("src/b.py", "z = 3\n")
        r = self.ratchet("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("baseline can come down", r.stdout)
        self.assertEqual(self.ratchet("lower").returncode, 0)
        self.assertEqual(self.baseline(), {"src/a.py": 1})
        self.assertEqual(self.ratchet("check").stdout.strip(), "ok")

    def test_a_broken_rule_command_fails_instead_of_counting_nothing(self):
        r = self.ratchet("add", "bad", "--command", "grep -rn TODO no-such-dir", "--reason", "r")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".ratchet", "bad.json")))

    def test_install_copies_the_script_word_for_word(self):
        self.assertEqual(self.ratchet("install", self.root).returncode, 0)
        with open(RATCHET, "rb") as a, open(os.path.join(self.root, "scripts", "ratchet.py"), "rb") as b:
            self.assertEqual(a.read(), b.read())


class CommentsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        subprocess.run(["git", "init", "-q", self.root], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        subprocess.run(["git", "-C", self.root, "add", rel], check=True)

    def comments(self, *paths):
        r = subprocess.run([sys.executable, RATCHET, "comments", *paths], capture_output=True, text=True,
                           cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.splitlines()

    def test_counts_comment_lines_in_python_typescript_and_shell(self):
        self.write("a.py", "x = 1  # set x\n# loop\ny = '# not a comment'\n")
        self.write("b.ts", "const u = 'http://x'; // the url\n/* one\n   two */\nconst s = `// no`;\n")
        self.write("c.sh", "echo $# \"# no\" # count\n# say hi\necho hi\n")
        self.assertEqual(self.comments(), ["a.py:1", "a.py:2", "b.ts:1", "b.ts:2", "b.ts:3", "c.sh:1", "c.sh:2"])

    def test_skips_why_comments_shebangs_licences_directives_and_docstrings(self):
        self.write("a.py", "#!/usr/bin/env python3\n# Copyright 2026 Someone\n# MIT licence\n"
                           '"""Usage: a.py"""\nimport os  # noqa: F401\n# why: the API rounds down\n')
        self.write("b.ts", "// SPDX-License-Identifier: MIT\n\n// @ts-expect-error old types\n"
                           "const x = 1; // Why: the vendor sends strings\n")
        self.assertEqual(self.comments(), [])

    def test_skips_generated_minified_and_untracked_files(self):
        self.write("gen.ts", "// @generated by protoc\n// field one\n")
        self.write("lib.min.js", "/* banner */\n")
        with open(os.path.join(self.root, "loose.py"), "w") as f:
            f.write("# untracked\n")
        self.assertEqual(self.comments(), [])

    def test_limits_to_the_paths_given(self):
        self.write("src/a.py", "# one\n")
        self.write("lib/b.py", "# two\n")
        self.assertEqual(self.comments("src"), ["src/a.py:1"])

    def test_a_new_comment_fails_the_starter_rule(self):
        self.write("a.py", "# old\n")
        cmd = f"{sys.executable} {RATCHET} comments"
        run = lambda *a: subprocess.run([sys.executable, RATCHET, *a], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(run("add", "comments", "--command", cmd, "--reason", "r").returncode, 0)
        self.write("b.py", "x = 1  # new\n")
        r = run("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("b.py: 1 (allowed 0)", r.stdout)


if __name__ == "__main__":
    unittest.main()
