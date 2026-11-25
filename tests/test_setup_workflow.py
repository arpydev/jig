import json
import os
import subprocess
import sys
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(CORE, "skills", "setup-workflow", "scripts")
GOOD = {"version": 1, "committed": False, "tracker": {"kind": "github"}, "checks": "pnpm check",
        "docs": {"glossary": "GLOSSARY.md", "adr": "docs/adr"}, "runData": ".claude/workflow-runs",
        "verifySkill": "verify-demo"}


def run(*args, env=None, cwd=None):
    return subprocess.run(list(args), capture_output=True, text=True, env=env, cwd=cwd, stdin=subprocess.DEVNULL)


class Repo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        run("git", "init", "-q", self.root)
        run("git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
        self.env = dict(os.environ, CLAUDE_HOME=os.path.join(self.root, "home"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)

    def settings(self, *args, repo=None):
        return run(sys.executable, os.path.join(SCRIPTS, "settings.py"), *args, "--repo", repo or self.root, env=self.env)


class SettingsTest(Repo):
    def test_good_settings_pass(self):
        self.write(".claude/workflow.json", json.dumps(GOOD))
        self.assertEqual(self.settings("check").stdout.strip(), "ok")

    def test_each_problem_is_reported(self):
        bad = dict(GOOD, tracker={"kind": "jira"}, steps={"grill": ["missing.md", "skill:nope"], "lunch": []})
        self.write(".claude/workflow.json", json.dumps(bad))
        r = self.settings("check")
        self.assertEqual(r.returncode, 1)
        for text in ("tracker.site", "tracker.keyPattern", "file not found: missing.md", "skill not installed: nope", "unknown step"):
            self.assertIn(text, r.stdout)

    def test_driver_settings_are_checked(self):
        bad = dict(GOOD, tracker={"kind": "github", "tickets": " "}, implementers=0, worktreeSetup="")
        self.write(".claude/workflow.json", json.dumps(bad))
        r = self.settings("check")
        self.assertEqual(r.returncode, 1)
        for text in ("tracker.tickets", "implementers", "worktreeSetup"):
            self.assertIn(text, r.stdout)
        good = dict(GOOD, tracker={"kind": "github", "tickets": "gh issue view"}, implementers=3, worktreeSetup="true")
        for kind in ("gitlab", "other"):
            self.write(".claude/workflow.json", json.dumps(dict(GOOD, tracker={"kind": kind})))
            self.assertEqual(self.settings("check").stdout.strip(), "ok")
        self.write(".claude/workflow.json", json.dumps(good))
        self.assertEqual(self.settings("check").stdout.strip(), "ok")

    def test_worker_agent_must_be_installed(self):
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, workerAgent="helper")))
        r = self.settings("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("workerAgent: agent not installed: helper", r.stdout)
        self.write("home/agents/helper.md", "x")
        self.assertEqual(self.settings("check").stdout.strip(), "ok")
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, workerAgent="")))
        self.assertIn("workerAgent must be", self.settings("check").stdout)

    def test_ratchet_copy_must_match_the_core(self):
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, ratchet="scripts/ratchet.py")))
        self.assertIn("file not found", self.settings("check").stdout)
        run(sys.executable, os.path.join(SCRIPTS, "ratchet.py"), "install", self.root)
        self.assertEqual(self.settings("check").stdout.strip(), "ok")
        with open(os.path.join(self.root, "scripts", "ratchet.py"), "a") as f:
            f.write("# edited\n")
        self.assertIn("differs from the core's copy", self.settings("check").stdout)

    def test_step_additions_that_exist_pass(self):
        self.write("q.md", "x")
        os.makedirs(os.path.join(self.root, "home", "skills", "demo"))
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, steps={"grill": ["q.md", "skill:demo"]})))
        self.assertEqual(self.settings("check").stdout.strip(), "ok")

    def test_get_reads_a_dotted_key(self):
        self.write(".claude/workflow.json", json.dumps(GOOD))
        self.assertEqual(self.settings("get", "tracker.kind").stdout.strip(), "github")
        self.assertEqual(self.settings("get", "tracker.site").returncode, 1)

    def test_domain_and_design_are_steps(self):
        self.write("d.md", "x")
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, steps={"domain": ["d.md"], "design": ["d.md"]})))
        self.assertEqual(self.settings("check").stdout.strip(), "ok")

    def test_steps_prints_each_addition_resolved(self):
        self.write("d.md", "x")
        os.makedirs(os.path.join(self.root, "home", "skills", "demo"))
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, steps={"design": ["d.md", "skill:demo"]})))
        r = self.settings("steps", "design")
        self.assertEqual(r.stdout.splitlines(), [os.path.join(self.root, "d.md"), "skill:demo"])
        self.assertEqual(self.settings("steps", "grill").stdout, "")

    def test_steps_paths_prints_skills_as_files_project_first(self):
        self.write("home/skills/demo/SKILL.md", "user")
        self.write("home/skills/both/SKILL.md", "user")
        self.write(".claude/skills/both/SKILL.md", "project")
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, steps={"review": ["skill:demo", "skill:both"]})))
        r = self.settings("steps", "review", "--paths")
        self.assertEqual(r.stdout.splitlines(), [os.path.join(self.root, "home/skills/demo/SKILL.md"),
                                                 os.path.join(self.root, ".claude/skills/both/SKILL.md")])
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, steps={"review": ["skill:gone"]})))
        self.assertEqual(self.settings("steps", "review", "--paths").returncode, 1)

    def test_steps_without_settings_prints_nothing(self):
        r = self.settings("steps", "domain")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(self.settings("steps", "lunch").returncode, 1)

    def test_model_prints_the_override_or_the_core_default(self):
        self.assertEqual(self.settings("model", "correctnessReviewer").stdout.strip(), "opus")
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, models={"correctnessReviewer": "sonnet"})))
        self.assertEqual(self.settings("model", "correctnessReviewer").stdout.strip(), "sonnet")
        self.assertEqual(self.settings("model", "implementer").stdout.strip(), "session")
        self.assertEqual(self.settings("model", "chef").returncode, 1)

    def test_unknown_model_role_fails_check(self):
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, models={"chef": "opus", "merger": "gpt"})))
        r = self.settings("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("models.chef: unknown role", r.stdout)
        self.assertIn("models.merger: unknown model gpt", r.stdout)

    def test_exclude_is_safe_to_rerun(self):
        self.write(".claude/workflow.json", json.dumps(GOOD))
        self.settings("exclude")
        self.settings("exclude")
        with open(os.path.join(self.root, ".git", "info", "exclude")) as f:
            lines = f.read().splitlines()
        self.assertEqual(lines.count("/.claude/workflow.json"), 1)
        self.assertEqual(lines.count("/.claude/skills/verify-demo"), 1)
        self.assertEqual(run("git", "-C", self.root, "status", "--porcelain").stdout, "")

    def test_committed_settings_are_not_excluded(self):
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, committed=True)))
        self.assertEqual(self.settings("never-commit").stdout.strip(), "")

    def test_worktree_finds_the_main_checkout(self):
        self.write(".claude/workflow.json", json.dumps(GOOD))
        wt = os.path.join(self.root, "wt")
        run("git", "-C", self.root, "worktree", "add", "-q", wt)
        self.assertEqual(self.settings("path", repo=wt).stdout.strip(), os.path.join(self.root, ".claude", "workflow.json"))


class ProjectSkillsTest(Repo):
    def make_skill(self, name):
        d = os.path.join(self.root, "pack", "skills", name)
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w") as f:
            f.write("x")
        return d

    def test_link_is_safe_to_rerun_and_excluded(self):
        src = self.make_skill("conventions")
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, projectSkills=[src])))
        self.assertEqual(self.settings("check").stdout.strip(), "ok")
        self.assertIn("linked", self.settings("link").stdout)
        self.assertIn("ok", self.settings("link").stdout)
        self.assertTrue(os.path.islink(os.path.join(self.root, ".claude", "skills", "conventions")))
        self.assertIn(".claude/skills/conventions", self.settings("never-commit").stdout)

    def test_link_reports_a_conflict(self):
        src = self.make_skill("conventions")
        os.makedirs(os.path.join(self.root, ".claude", "skills", "conventions"))
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, projectSkills=[src])))
        r = self.settings("link")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CONFLICT", r.stdout)

    def test_missing_project_skill_fails_check(self):
        self.write(".claude/workflow.json", json.dumps(dict(GOOD, projectSkills=["nowhere"])))
        self.assertIn("not a skill folder: nowhere", self.settings("check").stdout)


class SkeletonTest(Repo):
    def test_skeleton_maps_features_and_lists_routes(self):
        self.write("src/features/recipes/a.ts", "")
        self.write("src/features/recipes/a.test.ts", "")
        self.write("src/app/(app)/plan/page.tsx", "")
        self.write("ignored/x.test.ts", "")
        self.write(".gitignore", "ignored/\n")
        run("git", "-C", self.root, "add", "-A")
        script = os.path.join(SCRIPTS, "verify_skeleton.py")
        r = run(sys.executable, script, "verify-demo", "--repo", self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.root, ".claude", "skills", "verify-demo", "SKILL.md")) as f:
            text = f.read()
        self.assertIn("| recipes | `src/features/recipes/` | 1 test files |", text)
        self.assertIn("`src/app/(app)/plan/page.tsx`", text)
        self.assertNotIn("ignored", text)
        self.assertEqual(run(sys.executable, script, "verify-demo", "--repo", self.root).returncode, 1)


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.pack = os.path.join(self.tmp.name, "pack")
        os.makedirs(os.path.join(self.pack, "skills", "pack-skill"))
        os.makedirs(os.path.join(self.pack, "skills", "scoped"))
        with open(os.path.join(self.pack, "pack.json"), "w") as f:
            f.write('{"name": "demo", "projectSkills": ["scoped"]}')
        os.makedirs(os.path.join(self.pack, "agents"))
        with open(os.path.join(self.pack, "agents", "pack-worker.md"), "w") as f:
            f.write("x")
        self.env = dict(os.environ, CLAUDE_HOME=self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *args):
        return run("bash", os.path.join(CORE, "install.sh"), "--pack", self.pack, *args, env=self.env)

    def test_dry_run_changes_nothing(self):
        r = self.install("--dry-run")
        self.assertIn("would link", r.stdout)
        self.assertFalse(os.path.exists(self.home))

    def test_links_core_and_pack_and_is_safe_to_rerun(self):
        self.assertEqual(self.install().returncode, 0)
        self.assertTrue(os.path.islink(os.path.join(self.home, "skills", "setup-workflow")))
        self.assertTrue(os.path.islink(os.path.join(self.home, "skills", "pack-skill")))
        self.assertTrue(os.path.islink(os.path.join(self.home, "agents", "pack-worker.md")))
        self.assertFalse(os.path.exists(os.path.join(self.home, "skills", "scoped")))
        r = self.install()
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("linked    ", r.stdout)
        with open(os.path.join(self.home, "workflow-packs")) as f:
            self.assertEqual([os.path.realpath(p) for p in f.read().splitlines()], [os.path.realpath(self.pack)])

    def test_detect_lists_project_skills_of_installed_packs(self):
        self.install()
        repo = os.path.join(self.tmp.name, "repo")
        run("git", "init", "-q", repo)
        out = json.loads(run(sys.executable, os.path.join(SCRIPTS, "detect.py"), "--repo", repo, env=self.env).stdout)
        self.assertEqual(list(out["packProjectSkills"]), ["scoped"])

    def test_existing_folder_is_a_conflict_and_left_alone(self):
        os.makedirs(os.path.join(self.home, "skills", "pack-skill"))
        r = self.install()
        self.assertEqual(r.returncode, 1)
        self.assertIn("CONFLICT", r.stdout)
        self.assertFalse(os.path.islink(os.path.join(self.home, "skills", "pack-skill")))


    def test_backup_moves_the_existing_folder_and_links(self):
        old = os.path.join(self.home, "skills", "pack-skill")
        os.makedirs(old)
        with open(os.path.join(old, "mine.md"), "w") as f:
            f.write("keep me")
        self.assertIn("would back up", self.install("--backup", "--dry-run").stdout)
        self.assertFalse(os.path.islink(old))
        r = self.install("--backup")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(os.path.islink(old))
        with open(os.path.join(self.home, "skills-backup", "pack-skill", "mine.md")) as f:
            self.assertEqual(f.read(), "keep me")

    def test_backup_never_overwrites_an_earlier_backup(self):
        os.makedirs(os.path.join(self.home, "skills", "pack-skill"))
        os.makedirs(os.path.join(self.home, "skills-backup", "pack-skill"))
        r = self.install("--backup")
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists", r.stdout)
        self.assertFalse(os.path.islink(os.path.join(self.home, "skills", "pack-skill")))

    def test_core_skill_in_a_pack_is_a_duplicate(self):
        os.makedirs(os.path.join(self.pack, "skills", "setup-workflow"))
        r = self.install()
        self.assertIn("duplicate setup-workflow", r.stdout)
        self.assertEqual(os.readlink(os.path.join(self.home, "skills", "setup-workflow")), os.path.join(CORE, "skills", "setup-workflow"))

    def pack_hooks(self):
        folder = os.path.join(self.pack, "hooks")
        os.makedirs(os.path.join(folder, "checks"))
        for name in ("p.py", os.path.join("checks", "c.py")):
            with open(os.path.join(folder, name), "w") as f:
                f.write("")
        with open(os.path.join(folder, "hooks.json"), "w") as f:
            json.dump({"files": ["p.py", "checks/c.py"], "entries": [
                {"event": "PreToolUse", "matcher": "Bash", "command": "python3 {hooks}/p.py"}]}, f)

    def test_links_hooks_and_merges_their_entries(self):
        self.pack_hooks()
        r = self.install("--owner", "no")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        hooks = os.path.join(self.home, "hooks")
        self.assertEqual(os.readlink(os.path.join(hooks, "git-guard.py")), os.path.join(CORE, "hooks", "git-guard.py"))
        self.assertTrue(os.path.islink(os.path.join(hooks, "checks", "c.py")))
        with open(os.path.join(self.home, "settings.json")) as f:
            bash = [g for g in json.load(f)["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"][0]
        commands = [h["command"] for h in bash["hooks"]]
        self.assertIn(f"python3 -I {hooks}/git-guard.py", commands)
        self.assertIn(f"python3 {hooks}/p.py", commands)
        self.assertNotIn("added", self.install().stdout)

    def test_owner_is_recorded_and_defaults_to_false(self):
        self.install()
        record = os.path.join(self.home, "workflow-core.json")
        with open(record) as f:
            self.assertEqual(json.load(f), {"owner": False})
        self.install("--owner", "yes")
        with open(record) as f:
            self.assertEqual(json.load(f), {"owner": True})
        self.install()
        with open(record) as f:
            self.assertEqual(json.load(f), {"owner": True})
        self.assertEqual(self.install("--owner", "maybe").returncode, 2)

    def test_claude_md_imports_preferences_once(self):
        os.makedirs(self.home)
        with open(os.path.join(self.home, "CLAUDE.md"), "w") as f:
            f.write("# Mine")
        self.install()
        self.install()
        with open(os.path.join(self.home, "CLAUDE.md")) as f:
            self.assertEqual(f.read(), f"# Mine\n@{CORE}/preferences.md\n")

    def test_link_to_a_moved_core_is_relinked(self):
        dest = os.path.join(self.home, "skills", "setup-workflow")
        os.makedirs(os.path.dirname(dest))
        os.symlink(os.path.join(self.tmp.name, "old-core", "skills", "setup-workflow"), dest)
        self.assertIn("would relink", self.install("--dry-run").stdout)
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("relinked", r.stdout)
        self.assertEqual(os.readlink(dest), os.path.join(CORE, "skills", "setup-workflow"))
        self.assertFalse(os.path.exists(os.path.join(self.home, "skills-backup")))

    def test_import_of_a_moved_core_is_replaced(self):
        os.makedirs(self.home)
        with open(os.path.join(self.home, "CLAUDE.md"), "w") as f:
            f.write(f"@{self.tmp.name}/old-core/preferences.md\n# Mine\n")
        self.install()
        with open(os.path.join(self.home, "CLAUDE.md")) as f:
            self.assertEqual(f.read(), f"@{CORE}/preferences.md\n# Mine\n")


def unattributed(skills_dir):
    """Skills with an upstream/ folder whose own files never name Matt Pocock's licence."""
    out = []
    for s in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, s)
        if not os.path.isdir(os.path.join(d, "upstream")):
            continue
        named = False
        for root, dirs, fs in os.walk(d):
            dirs[:] = [x for x in dirs if x != "upstream"]
            for f in fs:
                if f.endswith(".md") and "LICENSE-mattpocock-skills" in open(os.path.join(root, f)).read():
                    named = True
        if not named:
            out.append(s)
    return out


def unexplained_without_upstream(skills_dir):
    """Skills that name Matt Pocock's licence but have no upstream/ folder and don't say why."""
    out = []
    for s in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, s)
        skill = os.path.join(d, "SKILL.md")
        if os.path.isdir(os.path.join(d, "upstream")) or not os.path.isfile(skill):
            continue
        text = open(skill).read()
        if "LICENSE-mattpocock-skills" in text and "no upstream/ snapshot" not in text:
            out.append(s)
    return out


class AttributionTest(unittest.TestCase):
    """Every skill taken from Matt Pocock's skills keeps his MIT licence and says so."""

    def test_core_forks_name_the_licence(self):
        self.assertTrue(os.path.isfile(os.path.join(CORE, "LICENSE-mattpocock-skills")))
        self.assertEqual(unattributed(os.path.join(CORE, "skills")), [])
        self.assertEqual(unexplained_without_upstream(os.path.join(CORE, "skills")), [])

    def test_fork_without_the_comment_fails(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "tdd", "upstream"))
            with open(os.path.join(d, "tdd", "SKILL.md"), "w") as f:
                f.write("---\nname: tdd\n---\n")
            with open(os.path.join(d, "tdd", "upstream", "SKILL.md"), "w") as f:
                f.write("LICENSE-mattpocock-skills\n")
            self.assertEqual(unattributed(d), ["tdd"])

    def test_fork_without_upstream_must_say_why(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "implement"))
            with open(os.path.join(d, "implement", "SKILL.md"), "w") as f:
                f.write("<!-- From mattpocock/skills (MIT, see ../../LICENSE-mattpocock-skills). -->\n")
            self.assertEqual(unexplained_without_upstream(d), ["implement"])


if __name__ == "__main__":
    unittest.main()


class SkillsUseKnownStepsTest(unittest.TestCase):
    """Every `settings.py steps <step>` and `settings.py model <role>` a core skill names must exist."""

    def test_core_skills_name_known_steps_and_roles(self):
        sys.path.insert(0, SCRIPTS)
        try:
            import settings
        finally:
            sys.path.pop(0)
        import re
        steps, roles = set(), set()
        for d, dirs, names in os.walk(os.path.join(CORE, "skills")):
            dirs[:] = [x for x in dirs if x != "upstream"]
            for n in names:
                if n.endswith(".md"):
                    with open(os.path.join(d, n), encoding="utf-8") as fh:
                        text = fh.read()
                    steps |= set(re.findall(r"settings\.py steps ([a-z]+)", text))
                    roles |= set(re.findall(r"settings\.py model ([a-zA-Z]+)", text))
                    for group in re.findall(r"`settings\.py model <role>` \(([^)]*)\)", text):
                        roles |= set(re.findall(r"`([a-zA-Z]+)`", group))
                    for group in re.findall(r"roles ((?:`[a-zA-Z]+`(?:, | and )?)+)", text):
                        roles |= set(re.findall(r"`([a-zA-Z]+)`", group))
        self.assertIn("review", steps)
        self.assertIn("correctnessReviewer", roles)
        self.assertEqual(steps - set(settings.STEPS), set())
        self.assertEqual(roles - set(settings.ROLES), set())


SKILL_REFS = os.path.join(CORE, "scripts", "skill_refs.py")


class SkillRefsTest(unittest.TestCase):
    """`skill_refs.py` fails when a skill names a script, file, step file or skill that doesn't exist."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pack = os.path.realpath(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        p = os.path.join(self.pack, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)

    def refs(self, *known):
        args = [sys.executable, SKILL_REFS, "--pack", self.pack]
        for k in known:
            args += ["--known", k]
        return run(*args)

    def test_core_names_only_what_exists(self):
        r = run(sys.executable, SKILL_REFS)
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_good_pack_passes(self):
        self.write("pack.json", json.dumps({"projectSkills": ["deliver"]}))
        self.write("steps/retro-demo.md", "x")
        self.write("skills/deliver/scripts/stage.py", "")
        self.write("skills/deliver/references/plan.md", "Back to [the skill](../SKILL.md).")
        self.write("skills/deliver/SKILL.md", "\n".join([
            "Run `python3 <this skill's folder>/scripts/stage.py` and `python3 ~/.claude/skills/retro/scripts/lookups.py`.",
            "Read [the plan](references/plan.md), `references/plan.md` and `steps/retro-demo.md`.",
            "Load the `retro` skill; the `retro` skill's `references/architecture-check.md` says when.",
            "Call the Skill tool with `tdd`. Ignore `references/<placeholder>.md`.",
            "```markdown", "[example](./src/GLOSSARY.md)", "```"]))
        r = self.refs()
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_each_missing_reference_is_reported(self):
        self.write("pack.json", json.dumps({"projectSkills": ["deliver"]}))
        self.write("skills/deliver/scripts/stage.py", "")
        self.write("skills/deliver/SKILL.md", "\n".join([
            "1 `python3 ~/.claude/skills/deliver/scripts/stage.py`",
            "2 `python3 ~/.claude/skills/retro/scripts/nope.py`",
            "3 `python3 ~/.claude/skills/ghost/scripts/x.py`",
            "4 `python3 <this skill's folder>/scripts/gone.py`",
            "5 [plan](references/plan.md)",
            "6 `references/missing.md`",
            "7 `steps/retro-gone.md`",
            "8 Use the `release-watch` skill.",
            "9 the `retro` skill's `references/nope.md`"]))
        r = self.refs()
        self.assertEqual(r.returncode, 1)
        lines = r.stdout.splitlines()
        self.assertEqual([int(l.split(":")[1]) for l in lines], list(range(1, 10)), r.stdout)
        self.assertIn("project skill", lines[0])
        self.assertIn("<this skill's folder>/scripts/stage.py", lines[0])

    def test_known_skill_is_accepted(self):
        self.write("skills/deliver/SKILL.md", "Load `plain-writing`.")
        self.assertEqual(self.refs().returncode, 1)
        self.assertEqual(self.refs("plain-writing").returncode, 0)
