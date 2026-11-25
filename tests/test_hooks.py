"""Tests for the core's hooks (hooks/) and scripts/hooks.py, which installs their entries."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(CORE, "hooks")
HOOKS_PY = os.path.join(CORE, "scripts", "hooks.py")


def run(hook, tool, tool_input, cwd="/tmp", env=None):
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": cwd, "session_id": "t"})
    out = subprocess.run([sys.executable, "-I", os.path.join(HOOKS, hook)], input=payload,
                         capture_output=True, text=True, check=True, env=env).stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


def bash(hook, command, cwd="/tmp"):
    return run(hook, "Bash", {"command": command}, cwd)


class Outbound(unittest.TestCase):
    H = "outbound-guard.py"

    def test_jira_writes_ask(self):
        for tool in ("createJiraIssue", "editJiraIssue", "addOrEditJiraIssueComment", "transitionJiraIssue", "executeWrite"):
            self.assertEqual(run(self.H, f"mcp__plugin_atlassian_atlassian__{tool}", {"body": "hi"}), "ask", tool)

    def test_jira_reads_pass(self):
        self.assertIsNone(run(self.H, "mcp__plugin_atlassian_atlassian__getJiraIssue", {"issueIdOrKey": "X-1"}))

    def test_bash_writes_ask(self):
        for cmd in ("git push origin x", "git -C /x push", "cd x && git push --force-with-lease",
                    "gh pr create --fill", "gh pr comment 1 -b hi", "gh pr review 1 --approve",
                    "gh issue create -t x", "gh api repos/a/b/issues -f body=x", "gh api -X POST repos/a/b"):
            self.assertEqual(bash(self.H, cmd), "ask", cmd)

    def test_bash_reads_pass(self):
        for cmd in ("git status", "git log --oneline", "git commit -m 'push the button'", "gh pr view 1",
                    "gh pr list", "gh api repos/a/b/pulls", "echo push"):
            self.assertIsNone(bash(self.H, cmd), cmd)

    def test_pack_checks_deny(self):
        with tempfile.TemporaryDirectory() as checks:
            with open(os.path.join(checks, "secret-word.py"), "w") as f:
                f.write("def check(text):\n    return 'no secrets' if 'sesame' in text else None\n")
            env = dict(os.environ, OUTBOUND_CHECKS_DIR=checks)
            self.assertEqual(run(self.H, "Bash", {"command": "gh pr comment 1 -b sesame"}, env=env), "deny")
            self.assertEqual(run(self.H, "Bash", {"command": "gh pr comment 1 -b hello"}, env=env), "ask")


class Git(unittest.TestCase):
    H = "git-guard.py"

    def test_force_push_denied(self):
        for cmd in ("git push --force", "git push -f origin x", "git push origin +x", "cd a && git push -uf origin x"):
            self.assertEqual(bash(self.H, cmd), "deny", cmd)

    def test_lease_allowed(self):
        self.assertIsNone(bash(self.H, "git push --force-with-lease origin x"))
        self.assertIsNone(bash(self.H, "git push -u origin x"))
        self.assertIsNone(bash(self.H, "git push --follow-tags"))

    def test_update_branch_denied(self):
        self.assertEqual(bash(self.H, "gh pr update-branch 12"), "deny")

    def test_pack_rules_not_in_the_core(self):
        self.assertIsNone(bash(self.H, "gh pr merge 12 --squash"))
        self.assertIsNone(bash(self.H, "git push", cwd="/tmp/pack-repo"))

    def test_merge_main_asks(self):
        self.assertEqual(bash(self.H, "git merge origin/main"), "ask")
        self.assertEqual(bash(self.H, "git pull origin main"), "ask")
        self.assertIsNone(bash(self.H, "git merge --abort"))
        self.assertIsNone(bash(self.H, "git pull --rebase"))
        self.assertIsNone(bash(self.H, "git pull --ff-only"))
        self.assertIsNone(bash(self.H, "git rebase origin/main"))


class Zsh(unittest.TestCase):
    def guard(self, cmd, shell="/bin/zsh"):
        return subprocess.run([sys.executable, os.path.join(HOOKS, "zsh-guard.py")], capture_output=True, text=True,
                              input=json.dumps({"tool_input": {"command": cmd}}), env=dict(os.environ, SHELL=shell))

    def test_unquoted_glob_and_equals_word_blocked(self):
        for cmd in ("grep -r --include=*.ts x .", "echo =====",):
            out = self.guard(cmd)
            self.assertTrue(out.returncode == 2 or out.stdout.strip(), cmd)

    def test_quoted_passes(self):
        out = self.guard("grep -r --include='*.ts' x .")
        self.assertEqual((out.returncode, out.stdout.strip()), (0, ""))

    def test_other_shells_pass(self):
        out = self.guard("echo =====", shell="/bin/bash")
        self.assertEqual((out.returncode, out.stdout.strip()), (0, ""))


class Docs(unittest.TestCase):
    H = "docs-guard.py"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.repo = os.path.join(self.root, "repo")
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.outside = os.path.join(self.root, "docs")

    def tearDown(self):
        self.tmp.cleanup()

    def settings(self, glossary, adr):
        os.makedirs(os.path.join(self.repo, ".claude"), exist_ok=True)
        with open(os.path.join(self.repo, ".claude", "workflow.json"), "w") as f:
            json.dump({"docs": {"glossary": glossary, "adr": adr}}, f)

    def write(self, path):
        return run(self.H, "Write", {"file_path": path, "content": "x"})

    def test_docs_outside_deny_new_files_inside(self):
        self.settings(os.path.join(self.outside, "GLOSSARY.md"), os.path.join(self.outside, "adr"))
        self.assertEqual(self.write(os.path.join(self.repo, "docs", "GLOSSARY.md")), "deny")
        self.assertEqual(self.write(os.path.join(self.repo, "docs", "adr", "0001-x.md")), "deny")
        self.assertEqual(self.write(os.path.join(self.repo, "ADR-0002.md")), "deny")
        self.assertIsNone(self.write(os.path.join(self.outside, "adr", "0001-x.md")))
        self.assertIsNone(self.write(os.path.join(self.repo, "docs", "notes.md")))

    def test_existing_files_can_be_edited(self):
        self.settings(os.path.join(self.outside, "GLOSSARY.md"), os.path.join(self.outside, "adr"))
        os.makedirs(os.path.join(self.repo, "docs"))
        with open(os.path.join(self.repo, "docs", "GLOSSARY.md"), "w") as f:
            f.write("old")
        self.assertIsNone(self.write(os.path.join(self.repo, "docs", "GLOSSARY.md")))

    def test_docs_inside_allow(self):
        self.settings("GLOSSARY.md", "docs/adr")
        self.assertIsNone(self.write(os.path.join(self.repo, "GLOSSARY.md")))
        self.assertIsNone(self.write(os.path.join(self.repo, "docs", "adr", "0001-x.md")))

    def test_each_path_is_its_own_toggle(self):
        self.settings("GLOSSARY.md", os.path.join(self.outside, "adr"))
        self.assertIsNone(self.write(os.path.join(self.repo, "GLOSSARY.md")))
        self.assertEqual(self.write(os.path.join(self.repo, "docs", "adr", "0001-x.md")), "deny")

    def test_no_settings_allow(self):
        self.assertIsNone(self.write(os.path.join(self.repo, "docs", "GLOSSARY.md")))

    def test_worktree_reads_the_main_checkout(self):
        self.settings(os.path.join(self.outside, "GLOSSARY.md"), os.path.join(self.outside, "adr"))
        subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                        "--allow-empty", "-m", "init"], check=True)
        tree = os.path.join(self.root, "tree")
        subprocess.run(["git", "-C", self.repo, "worktree", "add", "-q", tree], check=True)
        self.assertEqual(self.write(os.path.join(tree, "GLOSSARY.md")), "deny")


class InstallHooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)
        self.a = self.hooks_json("a", [{"event": "PreToolUse", "matcher": "Bash", "command": "python3 {hooks}/a.py"},
                                       {"event": "UserPromptSubmit", "command": "echo hi", "timeout": 5}])
        self.b = self.hooks_json("b", [{"event": "PreToolUse", "matcher": "Bash", "command": "python3 {hooks}/b.py"}])

    def tearDown(self):
        self.tmp.cleanup()

    def hooks_json(self, name, entries):
        path = os.path.join(self.tmp.name, name, "hooks.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"files": [], "entries": entries}, f)
        return path

    def install(self, *args):
        return subprocess.run([sys.executable, HOOKS_PY, "--home", self.home, *args], capture_output=True, text=True)

    def settings(self):
        with open(os.path.join(self.home, "settings.json")) as f:
            return json.load(f)

    def commands(self, event, matcher=None):
        for group in self.settings().get("hooks", {}).get(event, []):
            if group.get("matcher") == matcher:
                return [h["command"] for h in group["hooks"]]
        return []

    def test_adds_entries_and_keeps_other_settings(self):
        with open(os.path.join(self.home, "settings.json"), "w") as f:
            json.dump({"theme": "dark", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": "mine.sh"}]}]}}, f)
        self.assertEqual(self.install(self.a, self.b).returncode, 0)
        self.assertEqual(self.settings()["theme"], "dark")
        hooks = os.path.join(self.home, "hooks")
        self.assertEqual(self.commands("PreToolUse", "Bash"),
                         ["mine.sh", f"python3 {hooks}/a.py", f"python3 {hooks}/b.py"])
        self.assertEqual(self.commands("UserPromptSubmit"), ["echo hi"])

    def test_safe_to_rerun(self):
        self.install(self.a)
        before = self.settings()
        r = self.install(self.a)
        self.assertNotIn("added", r.stdout)
        self.assertEqual(self.settings(), before)

    def test_dry_run_writes_nothing(self):
        r = self.install("--dry-run", self.a)
        self.assertIn("would be added", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.home, "settings.json")))

    def test_removes_only_its_own_dropped_entries(self):
        with open(os.path.join(self.home, "settings.json"), "w") as f:
            json.dump({"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "mine.sh"}]}]}}, f)
        self.install(self.a, self.b)
        self.hooks_json("a", [{"event": "PreToolUse", "matcher": "Bash", "command": "python3 {hooks}/a.py"}])
        r = self.install(self.a)
        self.assertIn("removed", r.stdout)
        self.assertEqual(self.commands("UserPromptSubmit"), ["mine.sh"])
        hooks = os.path.join(self.home, "hooks")
        self.assertEqual(self.commands("PreToolUse", "Bash"), [f"python3 {hooks}/a.py", f"python3 {hooks}/b.py"])

    def test_entry_already_there_by_hand_is_adopted_not_duplicated(self):
        hooks = os.path.join(self.home, "hooks")
        with open(os.path.join(self.home, "settings.json"), "w") as f:
            json.dump({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": f"python3 {hooks}/a.py"}]}]}}, f)
        self.install(self.a)
        self.assertEqual(self.commands("PreToolUse", "Bash"), [f"python3 {hooks}/a.py"])

    def test_empty_groups_are_removed(self):
        self.install(self.b)
        self.hooks_json("b", [])
        self.install(self.b)
        self.assertEqual(self.settings().get("hooks"), {})

    def test_shipped_hooks_json_files_name_real_files(self):
        for folder in (HOOKS, os.path.join(os.path.dirname(CORE), "hooks")):
            path = os.path.join(folder, "hooks.json")
            if not os.path.exists(path):
                continue
            with open(path) as f:
                data = json.load(f)
            for name in data["files"]:
                self.assertTrue(os.path.isfile(os.path.join(folder, name)), name)
            for e in data["entries"]:
                if "{hooks}/" in e["command"]:
                    self.assertIn(e["command"].split("{hooks}/")[1].split()[0], data["files"], e["command"])


if __name__ == "__main__":
    unittest.main()
