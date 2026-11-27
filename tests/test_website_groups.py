"""The website build fails when website/src/lib/groups.ts and the folders in skills/ disagree.

This mirrors that rule so the project's checks catch it at each ticket's merge, without Node.
Run 1-8 left the Vercel build red for six merges because a new skill had no group yet.
"""
import os
import re
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def skill_folders(core):
    skills = os.path.join(core, "skills")
    return sorted(n for n in os.listdir(skills) if os.path.exists(os.path.join(skills, n, "SKILL.md")))


def grouped_skills(core):
    with open(os.path.join(core, "website", "src", "lib", "groups.ts"), encoding="utf-8") as f:
        text = f.read()
    names = []
    for block in re.findall(r"skills:\s*\[(.*?)\]", text, re.S):
        names += re.findall(r'"([a-z0-9-]+)"', block)
    return names


class WebsiteGroupsTest(unittest.TestCase):
    def test_every_skill_is_in_exactly_one_group_and_every_group_entry_is_a_skill(self):
        folders, grouped = skill_folders(CORE), grouped_skills(CORE)
        self.assertTrue(grouped, "no skills found in groups.ts; has its shape changed?")
        missing = [n for n in folders if n not in grouped]
        unknown = [n for n in grouped if n not in folders]
        twice = sorted({n for n in grouped if grouped.count(n) > 1})
        self.assertEqual((missing, unknown, twice), ([], [], []),
                         "website/src/lib/groups.ts is out of step with skills/ "
                         "(not in a group, no such skill, in two groups); the website build will fail")


if __name__ == "__main__":
    unittest.main()
