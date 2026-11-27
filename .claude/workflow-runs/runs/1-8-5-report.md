Ticket #5 is built and committed on `claude/1-8-5` as 9fa60bb, in the worktree /Volumes/Development/personal/jig/.claude/worktrees/1-8-5. `claude/1-8` was already merged in (it reported "Already up to date"). `drive.py checks 1-8 5` passes: 236 tests OK and the ratchet is ok.

**How the merged graph is made (the open item)**
- New script `skills/diagram/scripts/merge.mjs <before.json> <after.json> <out.json>` writes one graph from two:
  - items only in after are marked `added`;
  - items only in before are marked `removed`;
  - items in both are taken from after and marked `unchanged`;
  - any marks already in the inputs are ignored.
- It reuses compare's logic: I moved the `SECTIONS` table into `graph.mjs` and added a `pair()` helper there. `compare.mjs` and `merge.mjs` both use them, so nothing is copied, and the existing compare tests still pass.
- The plan graph is the current and expected graphs merged. The proof graph is the current and real graphs merged. Those two are what `compare.mjs` checks.
- `diagram/SKILL.md` now lists the Merge script.

**`drive.py diagram`**
- `drive.py diagram <spec> plan <current> <expected> [--ticket T]` writes `<runData>/runs/<spec>[-T]-plan.json`. It deletes any old proof and PR section, so a newly agreed plan needs a fresh proof.
- `drive.py diagram <spec> proof <before> <after> --kind K [--ticket T]` writes `-proof.json` and compares it with the plan.
  - On a mismatch it exits 1 and lists the differences.
  - On a match it prints the result line and writes `-pr.md` from the template `skills/implement-spec/references/pr-body.md`.
- While a ticket has a plan file, `drive.py checks <spec> <ticket>` and `drive.py merge` (even with `--approved`) fail until the proof matches. The check runs before the autonomy gate.
- `diagram` needs only the run's data folder, not a started run, so `implement` can use it with a ticket number as the run name.

**Acceptance criteria**
1. **Both skills say when to draw and when to check.**
   - `implement/SKILL.md`: one paragraph. Draw the plan diagram with the plan, with waiting following the autonomy level. Check the proof once the tests pass. A mismatch is a failing test. Graphs go in runData. Follow diagram's stop-and-ask when no kind covers the change.
   - `implement-spec/SKILL.md`: a short **Diagrams.** paragraph. The implementer bullet in step 4 says to draw before building and prove after the tests pass. Step 8 adds `<spec>-<ticket>-pr.md` to the PR body.
   - I wrote both in the writing-for-agents style and checked them myself. No separate review was run.
2. **A mismatch stops the run at every level.** `test_drive.DiagramTest.test_a_mismatch_stops_the_merge_at_level_2_until_the_proof_matches`:
   - at level 2, merge with no proof is refused;
   - a mismatching proof exits 1 with "changed edge Start -> Finish: mark removed, now unchanged";
   - `merge`, `merge --approved` and `checks` all exit 1 and the integration branch does not move;
   - a matching proof then lets checks and merge pass.
   - Also `test_a_new_plan_drops_the_old_proof`.
3. **Graph files go under the run's data folder.** `test_graph_files_are_written_under_the_run_data_folder`: only `s1-1-plan.json`, `s1-1-proof.json` and `s1-1-pr.md` appear in `<runData>/runs`, and nothing new appears in the repository.
4. **The PR body template has the result line and the collapsed Mermaid block.**
   - `PrBodyTemplateTest.test_template_has_the_result_line_and_a_collapsed_mermaid_block`
   - `test_a_match_writes_the_pr_section_from_the_template`, whose result line reads "Proof diagram matched the plan diagram (call-tree, 1 node added, 2 edges added, 1 group removed, 1 node removed, 2 edges removed)", followed by a ```` ```mermaid ```` block inside `<details>`.
5. **`docs/decisions.md` has the entry.** "Diagrams prove the work and then go" is under Trust, in the file's format. No test, as the ticket says.

**Test data**
- `tests/fixtures/diagram/run/`: `current.json`, `expected.json`, `after-match.json` and `after-mismatch.json`, with generic names (Start, Check, Finish, Legacy).
- `MergeTest` in `tests/test_diagram.py` has three tests: merge output against a hand-written literal, input marks ignored, and the merged plan compared with the matching and mismatching proofs.

**Break table** (every break restored from a backup and confirmed identical)

| Break | Tests that went red |
|---|---|
| merge swaps added/removed | before_and_after_merge, merged_plan_and_proof_compare, mismatch_stops (level 2), match_writes_pr_section |
| merge keeps input marks | marks_in_the_inputs_are_ignored, plus 6 others |
| pair() drops before-only items | before_and_after_merge, merged_plan_and_proof_compare, missing_edge_fails (existing), mismatch_stops, match_writes_pr_section |
| no diagram check at all | mismatch_stops, new_plan_drops_the_old_proof |
| a ticket with no plan treated as a mismatch | ticket_without_a_plan_merges_as_before, plus 6 existing DriveTests |
| missing proof passes | mismatch_stops, new_plan_drops_the_old_proof (first scripted break was wrong and showed no red; redone by hand and red) |
| `--approved` skips the diagram check | mismatch_stops, new_plan_drops_the_old_proof |
| checks ignore the diagram | mismatch_stops |
| a new plan keeps the old proof | new_plan_drops_the_old_proof |
| graphs written in the repository | graph_files_are_written_under_the_run_data_folder, match_writes_pr_section |
| PR section drops the diagram | match_writes_pr_section |
| result line not pluralised | match_writes_pr_section |
| template not collapsed | template_has_..._collapsed_mermaid_block, match_writes_pr_section |

**Worked around, skipped or open**
- **No PR body template existed in either skill**, so I created `skills/implement-spec/references/pr-body.md`, filled by `drive.py`. `implement` points at the `-pr.md` file this writes.
- **I restructured `tests/test_drive.py`.** The shared setup moved into a `RunRepo` base class so `DiagramTest` doesn't rerun every DriveTest. The existing tests are unchanged.
- **`DiagramTest` skips when Node isn't installed.**
- **A changed label shows as `unchanged` in the merged drawing.** An item in both graphs whose label changed between before and after is still caught by compare, because the plan's and proof's labels differ.
- **Nothing in Python reads the ledger's plan checkpoint.** "Waits per the autonomy level" for drawing the plan diagram is only wording in the skills. In implement-spec, the developer sees the plan diagram through the implementer's report at the level-0 merge.
- **For the orchestrator:** the integration branch's draft PR body should take each ticket's `-pr.md` in step 8. This run produced none, because no kind was used on a real ticket.
- **I removed my new comments** to satisfy the comment ratchet.

PASS
