"""Tests for update.sh and hooks/update-check.py, against a throwaway upstream with release tags."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


class Upstream(unittest.TestCase):
    """An upstream Jig with releases v0.1.0 (skill a) and v0.2.0 (skills a and b), cloned at v0.1.0."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.env = dict(os.environ, **GIT_ENV, CLAUDE_HOME=os.path.join(self.tmp, "home"))
        self.upstream = os.path.join(self.tmp, "upstream")
        os.makedirs(self.upstream)
        for f in ("install.sh", "update.sh", "preferences.md"):
            shutil.copy2(os.path.join(CORE, f), self.upstream)
        for d in ("scripts", "hooks"):
            shutil.copytree(os.path.join(CORE, d), os.path.join(self.upstream, d))
        self.git(self.upstream, "init", "-q", "-b", "main")
        self.release(self.upstream, "v0.1.0", add="a")
        self.release(self.upstream, "v0.2.0", add="b")
        self.core = os.path.join(self.tmp, "core")
        self.git(self.tmp, "clone", "-q", self.upstream, self.core)
        self.git(self.core, "-c", "advice.detachedHead=false", "checkout", "-q", "v0.1.0")
        self.home = self.env["CLAUDE_HOME"]
        os.makedirs(self.home)
        self.own(False)

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, capture_output=True, text=True,
                              check=True).stdout.strip()

    def release(self, repo, tag, add=None, remove=None):
        if add:
            os.makedirs(os.path.join(repo, "skills", add))
            with open(os.path.join(repo, "skills", add, "SKILL.md"), "w") as f:
                f.write(f"---\nname: {add}\n---\n")
        if remove:
            shutil.rmtree(os.path.join(repo, "skills", remove))
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", tag)
        self.git(repo, "tag", tag)

    def own(self, owner):
        with open(os.path.join(self.home, "workflow-core.json"), "w") as f:
            json.dump({"owner": owner}, f)

    def update(self, *args):
        return subprocess.run([os.path.join(self.core, "update.sh"), *args], env=self.env,
                              capture_output=True, text=True)

    def check(self):
        env = dict(self.env, JIG_CORE=self.core)
        out = subprocess.run([sys.executable, "-I", os.path.join(CORE, "hooks", "update-check.py")],
                             input="{}", env=env, capture_output=True, text=True, check=True).stdout.strip()
        return json.loads(out)["systemMessage"] if out else None

    def tag(self):
        return self.git(self.core, "describe", "--tags", "--exact-match")

    def skill_link(self, name):
        return os.path.join(self.home, "skills", name)


class Update(Upstream):
    def test_moves_to_latest_release_and_links_new_skills(self):
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.tag(), "v0.2.0")
        self.assertTrue(os.path.islink(self.skill_link("b")))

    def test_safe_to_rerun(self):
        self.update()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("latest release, v0.2.0", r.stdout)

    def test_dry_run_changes_nothing(self):
        r = self.update("--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("would move core from v0.1.0 to v0.2.0", r.stdout)
        self.assertEqual(self.tag(), "v0.1.0")
        self.assertFalse(os.path.lexists(self.skill_link("a")))

    def test_removes_links_to_skills_a_release_dropped(self):
        self.update()
        self.release(self.upstream, "v0.3.0", remove="a")
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.lexists(self.skill_link("a")))
        self.assertTrue(os.path.islink(self.skill_link("b")))

    def test_leaves_other_broken_links_alone(self):
        os.makedirs(os.path.join(self.home, "skills"))
        os.symlink(os.path.join(self.tmp, "elsewhere"), self.skill_link("mine"))
        self.update()
        self.assertTrue(os.path.lexists(self.skill_link("mine")))

    def test_refuses_a_core_with_uncommitted_changes(self):
        with open(os.path.join(self.core, "preferences.md"), "a") as f:
            f.write("local edit\n")
        r = self.update()
        self.assertEqual(r.returncode, 1)
        self.assertIn("uncommitted changes", r.stderr)
        self.assertEqual(self.tag(), "v0.1.0")

    def test_owner_pulls_the_current_branch(self):
        self.git(self.core, "checkout", "-q", "main")
        self.git(self.core, "reset", "-q", "--hard", "v0.1.0")
        self.own(True)
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.git(self.core, "rev-parse", "HEAD"), self.git(self.upstream, "rev-parse", "HEAD"))
        self.assertEqual(self.git(self.core, "rev-parse", "--abbrev-ref", "HEAD"), "main")

    def test_pulls_packs_with_a_remote_and_skips_others(self):
        pack_up = os.path.join(self.tmp, "pack-up")
        os.makedirs(pack_up)
        self.git(pack_up, "init", "-q", "-b", "main")
        self.release(pack_up, "p1", add="pa")
        pack = os.path.join(self.tmp, "pack")
        self.git(self.tmp, "clone", "-q", pack_up, pack)
        local = os.path.join(self.tmp, "local-pack")
        os.makedirs(os.path.join(local, "skills", "pl"))
        with open(os.path.join(self.home, "workflow-packs"), "w") as f:
            f.write(f"{pack}\n{local}\n")
        self.release(pack_up, "p2", add="pb")
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"skipped   {local}", r.stdout)
        self.assertTrue(os.path.islink(self.skill_link("pb")))
        self.assertTrue(os.path.islink(self.skill_link("pl")))

    def test_clears_the_check_cache(self):
        cache = os.path.join(self.home, "workflow-update-check.json")
        with open(cache, "w") as f:
            json.dump({"checked": int(time.time()), "latest": "v0.2.0"}, f)
        self.update()
        self.assertFalse(os.path.exists(cache))


class Check(Upstream):
    def test_prompts_when_a_newer_release_is_out(self):
        msg = self.check()
        self.assertIn("Jig v0.2.0 is out (you have v0.1.0)", msg)
        self.assertIn(os.path.join(self.core, "update.sh"), msg)

    def test_silent_on_the_latest_release(self):
        self.git(self.core, "-c", "advice.detachedHead=false", "checkout", "-q", "v0.2.0")
        self.assertIsNone(self.check())

    def test_silent_for_the_owner(self):
        self.own(True)
        self.assertIsNone(self.check())

    def test_uses_a_fresh_cache_without_asking_the_remote(self):
        self.git(self.core, "remote", "remove", "origin")
        with open(os.path.join(self.home, "workflow-update-check.json"), "w") as f:
            json.dump({"checked": int(time.time()), "latest": "v0.9.0"}, f)
        self.assertIn("Jig v0.9.0 is out", self.check())

    def test_asks_again_once_the_cache_is_a_day_old(self):
        with open(os.path.join(self.home, "workflow-update-check.json"), "w") as f:
            json.dump({"checked": int(time.time()) - 2 * 24 * 60 * 60, "latest": "v0.9.0"}, f)
        self.assertIn("Jig v0.2.0 is out", self.check())

    def test_silent_when_the_remote_cannot_be_reached(self):
        self.git(self.core, "remote", "set-url", "origin", os.path.join(self.tmp, "gone"))
        self.assertIsNone(self.check())

    def test_ignores_tags_that_are_not_releases(self):
        self.git(self.upstream, "tag", "v0.3.0-rc1")
        self.git(self.upstream, "tag", "nightly")
        self.assertIn("Jig v0.2.0 is out", self.check())


if __name__ == "__main__":
    unittest.main()
