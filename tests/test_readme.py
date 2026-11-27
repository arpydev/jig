"""Tests for the README's Scripts table."""
import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scripts_table_paths():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        return set(re.findall(r"^\| `([^`]+)` \|", f.read(), re.MULTILINE))


class ReadmeScriptsTableTest(unittest.TestCase):
    def test_every_named_script_exists(self):
        missing = [p for p in scripts_table_paths() if not os.path.isfile(os.path.join(ROOT, p))]
        self.assertEqual(missing, [])

    def test_every_python_script_has_a_row(self):
        found = [os.path.relpath(p, ROOT) for pattern in ("scripts/*.py", "skills/*/scripts/*.py")
                 for p in glob.glob(os.path.join(ROOT, pattern))]
        self.assertIn("skills/writing-for-agents/scripts/skill_overlap.py", found)
        self.assertEqual(sorted(set(found) - scripts_table_paths()), [])


if __name__ == "__main__":
    unittest.main()
