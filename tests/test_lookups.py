"""Tests for the retro's lookups.py."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "retro", "scripts")
sys.path.insert(0, HERE)
import lookups  # noqa: E402

SCRIPTS = {"review-gather", "transcript.py"}


def developer(text):
    return {"type": "user", "message": {"content": text}}


def call(call_id, name, tool_input):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}]}}


def result(call_id, text):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": call_id, "content": text}]}}


class LookupsTest(unittest.TestCase):
    def transcript(self, *entries):
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")
        handle.write("not json\n")
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_counts_exploration_with_result_sizes_and_developer_markers(self):
        path = self.transcript(
            developer("Which PRs belong to ABC-1?"),
            call("a", "Grep", {"pattern": "ABC-1", "path": "cdk"}), result("a", "x" * 1500),
            call("b", "Bash", {"command": "cd repo && gh pr list --search ABC-1"}), result("b", "y" * 10),
            call("c", "Edit", {"file_path": "f.ts"}), result("c", "ok"),
        )
        out = lookups.report([path], scripts=SCRIPTS)
        self.assertIn("Exploration calls: 2 (results 1.5k chars)", out)
        self.assertIn("--- developer: Which PRs belong to ABC-1?", out)
        self.assertIn("'ABC-1' cdk", out)
        self.assertIn("gh pr list", out)
        self.assertNotIn("f.ts", out)
        self.assertNotIn("xxx", out)  # result contents are never printed

    def test_script_runs_are_counted_not_explored(self):
        path = self.transcript(
            call("a", "Bash", {"command": "~/.claude/skills/my-skill/scripts/review-gather ABC-1"}),
            call("b", "Bash", {"command": "python3 -I /x/transcript.py s.jsonl > t.txt"}),
            call("c", "Bash", {"command": "sed -n 1,15p scripts/review-gather"}),
        )
        out = lookups.report([path], scripts=SCRIPTS)
        self.assertIn("Script runs: review-gather x1, transcript.py x1", out)
        self.assertIn("Exploration calls: 1", out)  # reading a script's source is exploration

    def test_classifies_bash_commands(self):
        reads = ["git -C /repo log --oneline -5", "grep -rn foo .", "sed -n 1,5p f",
                 "aws dynamodb get-item --table t", "gh pr view 12", "FOO=1 cat f | wc -l"]
        writes = ["cat > retros/x.md <<'EOF'\nhello\nEOF", "git commit -m x", "gh pr merge 12", "gh api -X POST repos/x", "sed -i '' s/a/b/ f",
                  "pnpm run test", "aws s3 cp a b", "mv a b"]
        for command in reads:
            self.assertTrue(lookups.is_read_bash(command), command)
        for command in writes:
            self.assertFalse(lookups.is_read_bash(command), command)

    def test_read_type_mcp_calls_only(self):
        self.assertTrue(lookups.is_exploration("mcp__plugin_atlassian_atlassian__getJiraIssue", {}))
        self.assertTrue(lookups.is_exploration("mcp__plugin_atlassian_atlassian__searchJiraIssuesUsingJql", {}))
        self.assertFalse(lookups.is_exploration("mcp__plugin_atlassian_atlassian__createJiraIssue", {}))

    def test_skill_file_reads_are_left_out_and_mcp_names_shortened(self):
        path = self.transcript(
            call("a", "Bash", {"command": "cat ~/.claude/skills/my-skill/references/plan.md"}),
            call("b", "mcp__plugin_atlassian_atlassian__getJiraIssue", {"issueIdOrKey": "ABC-1"}),
        )
        out = lookups.report([path], scripts=SCRIPTS)
        self.assertIn("Exploration calls: 1", out)
        self.assertIn("1 skill-file reads left out", out)
        self.assertIn("mcp:getJiraIssue", out)
        self.assertNotIn("plan.md", out)

    def test_scripts_only(self):
        path = self.transcript(call("a", "Grep", {"pattern": "x"}))
        self.assertEqual(lookups.report([path], scripts_only=True, scripts=SCRIPTS), "Script runs: none")

    def test_finds_workflow_scripts_next_to_itself(self):
        found = lookups.workflow_scripts(lookups.skills_root())
        self.assertIn("lookups.py", found)
        self.assertNotIn("test_lookups.py", found)

    def test_missing_transcript_fails_loudly(self):
        run = subprocess.run([sys.executable, "-I", os.path.join(HERE, "lookups.py"), "/no/such.jsonl"],
                             capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("No such transcript", run.stderr)


if __name__ == "__main__":
    unittest.main()
