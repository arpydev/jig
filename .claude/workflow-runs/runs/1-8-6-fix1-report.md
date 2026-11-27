Fix for ticket #6 (run 1-8), branch `claude/1-8-6`.

I added a test for the README Scripts table, which was the one criterion still checked only by eye. It is committed and `drive.py checks 1-8 6` passes.

**What changed**
- New file `/Volumes/Development/personal/jig/.claude/worktrees/1-8-6/tests/test_readme.py` with two general checks:
  - `test_every_named_script_exists`: every path in a README Scripts table row exists on disk.
  - `test_every_python_script_has_a_row`: every `scripts/*.py` and `skills/*/scripts/*.py` has a row in the table, and `skill_overlap.py` is among them.
- It only checks Python scripts. The diagram `.mjs` helpers and the `hitl-loop` template have no rows today, so including them would fail at once.
- Commit: "Test the README Scripts table against the scripts on disk", with two "Adds…" bullets.

**Red/green proof** (README copied to a backup, broken, then restored from the backup, `cmp` identical and `git diff` clean)

| Break | Tests that went red |
|---|---|
| `skill_overlap.py` row removed | `test_every_python_script_has_a_row` |
| `lookups.py` row renamed to a path that doesn't exist | `test_every_named_script_exists` and `test_every_python_script_has_a_row` |
| README restored | both pass |

**Checks**
- Merging `claude/1-8` changed nothing ("Already up to date").
- `drive.py checks 1-8 6` passed: 246 tests OK (244 before, plus these 2). Log: `/Volumes/Development/personal/jig/.claude/workflow-runs/runs/1-8-checks-6.log`
- The other criteria still hold. The `skill_overlap` tests and the `skill_refs` test that cover the writing-for-agents and retro criteria are part of that passing run, and no other files changed.

**Still open**
- Orchestrator item: paste the real-install output on the PR to close the last criterion. Leave out the line with the two workplace pack skills (pair 2), as the implementer said.
- History, nothing to redo:
  - The implementer's original build was not strictly test-first.
  - Its seams were not agreed with the developer.
  - In this fix I also chose the README as the test's seam without asking, because I had no way to ask from a subagent.

PASS
