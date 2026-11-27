"""Tests for release.sh, against a throwaway bare origin and a fake gh."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


class Release(unittest.TestCase):
    """A core on main at v1.0.0, with a bare origin."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.gh_log = os.path.join(self.tmp, "gh.log")
        gh = os.path.join(self.tmp, "gh")
        with open(gh, "w") as f:
            f.write(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{self.gh_log}"\n')
        os.chmod(gh, 0o755)
        self.env = dict(os.environ, **GIT_ENV, JIG_GH=gh)
        self.origin = os.path.join(self.tmp, "origin.git")
        self.git(self.tmp, "init", "-q", "--bare", "-b", "main", self.origin)
        self.core = os.path.join(self.tmp, "core")
        self.git(self.tmp, "clone", "-q", self.origin, self.core)
        self.git(self.core, "checkout", "-q", "-b", "main")
        shutil.copy2(os.path.join(CORE, "release.sh"), self.core)
        self.commit("Add release.sh")
        self.git(self.core, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
        self.git(self.core, "push", "-q", "origin", "main", "v1.0.0", "v1.0.0^{commit}:refs/heads/release")

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, capture_output=True, text=True,
                              check=True).stdout.strip()

    def commit(self, title):
        self.git(self.core, "commit", "-q", "--allow-empty", "-m", title)

    def release(self, *args):
        return subprocess.run([os.path.join(self.core, "release.sh"), *args], env=self.env,
                              capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def origin_tags(self):
        return self.git(self.origin, "tag").split()

    def test_a_new_skill_is_a_minor_release(self):
        self.commit("Add the status-flow skill")
        self.commit("Fix a typo in grilling")
        r = self.release("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("v1.1.0", self.origin_tags())
        with open(self.gh_log) as f:
            args = f.read().split("\n")
        self.assertEqual(args[:2], ["release", "create"])
        self.assertIn("v1.1.0", args)
        self.assertIn("- Add the status-flow skill\n- Fix a typo in grilling", "\n".join(args))

    def test_release_branch_points_at_the_new_tag(self):
        self.commit("Add a skill")
        r = self.release("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.git(self.origin, "rev-parse", "release"), self.git(self.origin, "rev-parse", "v1.1.0^{commit}"))

    def test_second_release_fast_forwards_release(self):
        self.commit("Add a skill")
        self.release("--yes")
        self.commit("Add another skill")
        r = self.release("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.git(self.origin, "rev-parse", "release"), self.git(self.origin, "rev-parse", "v1.2.0^{commit}"))

    def test_never_overwrites_a_release_branch_that_moved_elsewhere(self):
        other = os.path.join(self.tmp, "other")
        self.git(self.tmp, "clone", "-q", "-b", "release", self.origin, other)
        self.git(other, "commit", "-q", "--allow-empty", "-m", "Commit to release by hand")
        self.git(other, "push", "-q", "origin", "release")
        moved = self.git(other, "rev-parse", "HEAD")
        self.commit("Add a skill")
        r = self.release("--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.git(self.origin, "rev-parse", "release"), moved)

    def test_only_fixes_is_a_patch_release(self):
        self.commit("Fix update.sh on a detached HEAD")
        self.commit("Fixes the hook timeout")
        r = self.release("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("v1.0.1", self.origin_tags())

    def test_major_only_by_flag(self):
        self.git(self.core, "tag", "-a", "v1.4.2", "-m", "v1.4.2")
        self.commit("Add a big change")
        r = self.release("--major", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("v2.0.0", self.origin_tags())

    def test_pushes_unpushed_commits_with_the_tag(self):
        self.commit("Add a skill")
        self.release("--yes")
        self.assertEqual(self.git(self.origin, "rev-parse", "main"), self.git(self.core, "rev-parse", "HEAD"))

    def test_dry_run_changes_nothing(self):
        self.commit("Add a skill")
        r = self.release("--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Release v1.1.0 (last: v1.0.0)", r.stdout)
        self.assertIn("- Add a skill", r.stdout)
        self.assertNotIn("v1.1.0", self.git(self.core, "tag").split())
        self.assertFalse(os.path.exists(self.gh_log))
        self.assertEqual(self.git(self.origin, "rev-parse", "release"), self.git(self.origin, "rev-parse", "v1.0.0^{commit}"))

    def test_nothing_to_release(self):
        r = self.release("--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing to release", r.stdout)
        self.assertEqual(self.origin_tags(), ["v1.0.0"])

    def test_asks_without_yes_and_refuses_with_no_terminal(self):
        self.commit("Add a skill")
        r = self.release()
        self.assertEqual(r.returncode, 1)
        self.assertIn("rerun with --yes", r.stderr)
        self.assertEqual(self.origin_tags(), ["v1.0.0"])

    def test_refuses_when_behind_origin(self):
        other = os.path.join(self.tmp, "other")
        self.git(self.tmp, "clone", "-q", self.origin, other)
        self.git(other, "commit", "-q", "--allow-empty", "-m", "Add elsewhere")
        self.git(other, "push", "-q", "origin", "main")
        self.commit("Add a skill")
        r = self.release("--yes")
        self.assertEqual(r.returncode, 1)
        self.assertIn("behind origin/main", r.stderr)

    def test_refuses_off_main(self):
        self.git(self.core, "checkout", "-q", "-b", "feature")
        self.commit("Add a skill")
        r = self.release("--yes")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cut from main", r.stderr)

    def test_ignores_tags_that_are_not_releases(self):
        self.git(self.core, "tag", "v9.0.0-rc1")
        self.commit("Add a skill")
        r = self.release("--dry-run")
        self.assertIn("Release v1.1.0", r.stdout)


class WebsiteDeploys(unittest.TestCase):
    def test_vercel_does_not_deploy_from_main(self):
        with open(os.path.join(CORE, "website", "vercel.json")) as f:
            config = json.load(f)
        self.assertIs(config["git"]["deploymentEnabled"]["main"], False)


if __name__ == "__main__":
    unittest.main()
