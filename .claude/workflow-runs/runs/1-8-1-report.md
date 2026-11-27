Ticket #1 (Add the ast skill) is built on `claude/1-8-1`, committed as 5d7924b. `drive.py checks 1-8 1` passed: 172 tests OK plus the ratchet. Merging `claude/1-8` was a no-op because the branch already contained its tip. Nothing was pushed, and no issue or PR was touched.

**What changed**
- New skill `skills/ast/SKILL.md` (31 lines).
- New lookup script `skills/ast/scripts/ast_tool.py`:
  - `find <language>` looks first in the repository's `node_modules`. It knows `typescript` and `ts-morph` for TypeScript, and `typescript`, `@babel/parser` and `acorn` for JavaScript.
  - If one tool is installed, it prints it and exits 0.
  - If there are several or none, it uses `ast.<language>` from the project settings if set.
  - Otherwise it exits 2 with every candidate listed (several installed) or exits 3 printing nothing (none installed). Both tell the agent to ask the developer.
  - `save <language> <tool>` saves the pick to the settings.
- `skills/setup-workflow/scripts/settings.py` gains `set <dotted.key> <value>`. It is generic, keeps every other setting, and is what `save` calls, because skills write settings only through `settings.py`.
- `skills/setup-workflow/references/settings.md` gains a row for the `ast` key. `README.md`'s scripts table gains `ast_tool.py`.
- Tests are in `tests/test_ast.py`.

**Acceptance criteria**
1. The repository's own tool is returned: `test_local_typescript_is_returned`, plus `test_the_repository_tool_comes_before_the_settings`.
2. The settings tool is returned when the repository has none: `test_settings_tool_is_returned_when_the_repository_has_none`.
3. With several candidates or none, it reports that and makes no choice:
   - `test_two_local_candidates_are_both_listed_and_neither_chosen` (exit 2, both paths printed, "ask the developer").
   - `test_no_candidate_says_so_and_prints_nothing` (exit 3).
   - The SKILL.md says the developer always picks.
4. The saved choice is found on the next lookup: `test_saved_choice_is_found_on_the_next_lookup` (two installed, then save, then find returns the pick). Also `test_saving_keeps_the_other_settings` and `test_saving_without_settings_fails_and_points_to_setup`.
5. SKILL.md lists what each suggestion must say and stays short: `test_skill_says_what_each_suggestion_must_cover_and_stays_short`. It checks for "what it is", "trade-off", "across files", "two to four" and the save command, and that the file is under 60 lines. I also reviewed it against `writing-for-agents`: the description leads with the trigger, the steps end on exit codes, and it states the positive target ("ask rather than choosing one yourself").
6. No `npm` command in the settings reference: `test_settings_reference_names_no_npm_command`.

**Break table** (each break made from a backup copy, tests run, file restored; every test went red at least once)

| Break | Tests that failed |
|---|---|
| Repository lookup finds nothing | test_local_typescript_is_returned, test_saved_choice_is_found_on_the_next_lookup, test_the_repository_tool_comes_before_the_settings, test_two_local_candidates_are_both_listed_and_neither_chosen |
| Settings fallback removed | test_saved_choice_is_found_on_the_next_lookup, test_settings_tool_is_returned_when_the_repository_has_none |
| Settings checked before the repository | test_the_repository_tool_comes_before_the_settings |
| Several candidates: first one picked | test_saved_choice_is_found_on_the_next_lookup, test_two_local_candidates_are_both_listed_and_neither_chosen |
| No candidate: exits 0 | test_no_candidate_says_so_and_prints_nothing |
| No candidate: "ask" message dropped | test_no_candidate_says_so_and_prints_nothing |
| Save drops the other settings | test_saving_keeps_the_other_settings |
| Save writes nothing | test_saved_choice_is_found_on_the_next_lookup, test_saving_keeps_the_other_settings |
| No-settings message loses "setup-workflow" | test_saving_without_settings_fails_and_points_to_setup |
| SKILL.md drops "trade-off" | test_skill_says_what_each_suggestion_must_cover_and_stays_short |
| SKILL.md drops "across files" | test_skill_says_what_each_suggestion_must_cover_and_stays_short |
| SKILL.md padded past the line limit | test_skill_says_what_each_suggestion_must_cover_and_stays_short |
| settings.md gains `npm run check` | test_settings_reference_names_no_npm_command |

**Open points and decisions**
- **No core skill line limit exists.** Nothing in `writing-for-agents` or the scripts sets one. I set `SKILL_LINE_LIMIT = 60` in `tests/test_ast.py` for this skill only. If the core should have a shared limit, that needs deciding.
- **The npm part was already done.** `settings.md` already had no `npm` command on both `main` and `claude/1-8`. The new grep test was green from the start, so its value is that it fails if `npm` returns, which the last break shows.
- **Order rule where the ticket was ambiguous.** One installed tool beats the settings, as the ticket orders. When several are installed, a saved choice wins; without that, criterion 4 could not hold in the two-candidate case.
- **Fixtures are built in temporary folders, not committed under `tests/`.** The fixture repos (local TypeScript, none, two candidates) are created inside the tests, as the existing tests do, rather than as committed `node_modules` folders. All fixture data is fictional.
- **Test seams were not confirmed with a developer.** The tdd skill asks for that, but there was no developer to ask in this run. I tested only at the ticket's own interface: the `ast_tool.py find` and `save` commands.
- **Only TypeScript and JavaScript are found automatically.** Other languages rely on the saved setting. `save` needs `.claude/workflow.json` to exist; without it, it fails and says to run `setup-workflow`.

PASS
