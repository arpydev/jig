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


if __name__ == "__main__":
    unittest.main()
