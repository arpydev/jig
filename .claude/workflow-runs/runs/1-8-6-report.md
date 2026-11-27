Ticket #6 (run 1-8) is built and committed on `claude/1-8-6`. The branch already contained `claude/1-8`, so the merge changed nothing. `drive.py checks 1-8 6` passes: 244 tests OK, ratchet ok. Nothing was pushed, and no PR was opened or issue touched.

Commits: 48e6bfc "Report skill overlaps when a skill is written and at the retro's step-back", then 07f10fa "Mark the alias test's comment with why" (the comments ratchet failed the first checks run).

**Files**
- New: `/Volumes/Development/personal/jig/.claude/worktrees/1-8-6/skills/writing-for-agents/scripts/skill_overlap.py` (standard library only, read-only).
- New: `/Volumes/Development/personal/jig/.claude/worktrees/1-8-6/tests/test_skill_overlap.py`.
- New fixtures under `/Volumes/Development/personal/jig/.claude/worktrees/1-8-6/tests/fixtures/skill_overlap/`:
  - a core: grilling, domain-modeling, alias grill-me, ship-it, draw
  - a pack: release-train
  - a plugin: toolbox, with pipeline and rollout
  - `projects/` with four `.jsonl` transcripts. They include a subagent transcript, a resumed session that repeats a call ID, a `/clear` command and a line that is not JSON. All content is invented.
- Edited: `skills/writing-for-agents/SKILL.md` (new paragraph and a Local changes row), `skills/retro/SKILL.md` (the every-fifth step-back section) and `README.md` (Scripts table row).

**Acceptance criteria**
1. **One row per skill across core, packs and plugins, with every field:** proven by `test_one_row_per_skill_across_core_pack_and_plugin` and `test_loads_and_loaded_by`; the load count is covered by test 3.
   - Packs come from `<home>/workflow-packs`, plugins from `plugins/installed_plugins.json`.
   - The line count is `SKILL.md` lines.
2. **Alias flagged and never paired:** `test_alias_is_flagged_and_never_paired`.
   - The fixture grill-me loads grilling and quotes the same phrase "grill me".
   - ship-it is a near miss: developer-only and loads grilling, but does more, so it is not flagged.
   - The rule: developer-only (`disable-model-invocation: true`), loads at least one skill, and every body line outside HTML comments names a skill it loads.
3. **Load counts from transcripts, with the oldest date:** `test_load_counts_from_skill_calls_and_typed_commands` and `test_no_transcripts_says_so`.
   - It counts Skill tool calls (each call ID once) and typed `<command-name>/x</command-name>` commands, including subagent transcripts; release-train and draw are never loaded.
   - The oldest date printed is 2026-01-05.
4. **Top 10 pairs, quoted phrase first:** `test_shared_quoted_phrase_ranks_above_word_overlap`.
   - ship-it with release-train (shared "ship it", word overlap about 0.1) ranks above ship-it with pipeline (word overlap 0.4); the unrelated draw with domain-modeling is absent.
   - Word overlap is Jaccard over the "Use when…" clause after stopwords, or the whole description when there is no "Use when". Threshold 0.2.
5. **Plugin skills read-only:** `test_plugin_is_read_only_in_rows_and_pairs`. I also left out pairs where both skills are plugin skills, since neither could be changed: `test_two_plugin_skills_are_never_paired`.
6. **`writing-for-agents` names the script:** it now says to run `python3 -I ~/.claude/skills/writing-for-agents/scripts/skill_overlap.py` before creating a skill, and to extend an existing skill that covers the job. Proven by `SkillRefsTest.test_core_names_only_what_exists` (`skill_refs.py` exits 0); renaming the path turns that test red.
7. **Retro step-back:** it runs the `writing-for-agents` skill's `scripts/skill_overlap.py` and proposes at most one merge or removal, approved like any other retro change.
   - On an approved merge it copies both skills to `$TMPDIR`, folds B into A, then deletes B's folder and its `website/src/lib/groups.ts` entry.
   - It runs `<core>/scripts/no_regression.py` with old set to the copies and new to A, shows the lost lines, and keeps B as an alias only if the developer still types `/B`. A removal deletes the folder and group entry the same way.
   - Proven by the same `skill_refs` test; renaming the path turns it red.
8. **README Scripts table:** `README.md` line 50 has the row for `skills/writing-for-agents/scripts/skill_overlap.py`.
9. **Real install:** I ran it once, read-only, against the real `~/.claude`. Nothing from it went into the repository. Relevant output:

```
transcripts: 401 read, oldest 2026-08-04
| grill-me | core | 9 | grilling | - | alias | 0 | A relentless interview to sharpen a plan or design. |
| grill-with-docs | core | 9 | grilling, domain-modeling | - | alias | 3 | A relentless interview ...
| implement | core | 23 | tdd, review-change | - | - | 0 | Implement a piece of work based on a spec or set of tickets. |
| implement-spec | core | 72 | tdd, review-change, grade-run, retro | - | - | 3 | Implement the result of /to-spec and /to-tickets in code. |
Pairs most likely to overlap (top 10; alias skills and plugin-only pairs left out):
1. implement ~ implement-spec: word overlap 0.33 (implement, spec, tickets)
2. (a pair of two workplace pack skills; redacted from the public copy)
3. grade-run ~ retro: word overlap 0.22 (reaches, retro, run, step)
4. comment-report ~ improve-codebase-architecture: word overlap 0.2 (...)
```

The report had 59 rows: 26 core, 7 from a workplace pack, and 26 from plugins. Pair 2 is two workplace pack skills; leave that line out of the PR paste. (Redacted from the public copy.)

**Break table** (each break applied, the two test targets run, then the file restored from a backup and checked identical; every test went red at least once):

| Break | Tests that went red |
|---|---|
| packs skipped | one_row, load_counts, shared_quoted_phrase |
| plugin name prefix dropped | one_row, load_counts, plugin_read_only, shared_quoted_phrase |
| loads never found | loads_and_loaded_by, alias, shared_quoted_phrase |
| alias = any developer-only skill that loads | alias, plugin_read_only, shared_quoted_phrase |
| aliases put in pairs | alias, shared_quoted_phrase |
| plugin-with-plugin pairs kept | two_plugin_skills_never_paired |
| no Skill call-ID dedupe | load_counts |
| typed commands ignored | load_counts |
| newest date instead of oldest | load_counts, plugin_read_only |
| leading `/` on skill input kept | load_counts |
| phrases not ranked first | shared_quoted_phrase |
| quoted phrases ignored | shared_quoted_phrase |
| read-only label on pairs dropped | plugin_read_only |
| YAML `\"` unescape dropped | one_row |
| "none in" message changed | no_transcripts_says_so |
| subagent transcripts skipped | load_counts |
| writing-for-agents names a wrong script path | SkillRefsTest.test_core_names_only_what_exists |
| retro names a wrong script path | SkillRefsTest.test_core_names_only_what_exists |

**Open, worked around or not done**
- **Orchestrator to do:** paste the real-install output above on the PR to close the last criterion. I can't do that from this branch.
- **Not strictly test-first:** I wrote all of the test file, saw it fail because the module didn't exist, then wrote the whole script at once, instead of one test and one piece of code at a time. The break table stands in for the missing red runs.
- **Seams not confirmed with the developer:** the tdd skill wants the tested seams agreed first, and I had no way to ask from a subagent. I tested at `report()` and the CLI output.
- **Choices beyond the ticket:** plugin-with-plugin pairs are left out, and the line count is `SKILL.md` lines only. Both are stated in the script's opening comment.
- **README check is by eye:** no test checks the Scripts table row.

ISSUES
