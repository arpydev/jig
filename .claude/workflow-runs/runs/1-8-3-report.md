Ticket #3 (run 1-8) is built and committed on `claude/1-8-3` as commit 54b93b1, "Add the status-flow diagram kind". `claude/1-8` was merged in first ("Already up to date"). `drive.py checks 1-8 3` passed: 212 tests OK, 0 skipped, ratchet `ok` (log: /Volumes/Development/personal/jig/.claude/workflow-runs/runs/1-8-checks-3.log). Nothing was pushed, no PR was opened and no issue was touched.

**What was built**, under /Volumes/Development/personal/jig/.claude/worktrees/1-8-3/:
- `skills/diagram/kinds/status-flow/scripts/extract.mjs`: reads a TypeScript state machine and writes the shared graph file. You run it as `extract.mjs <file.ts> --states <type> [--field status] [--typescript <path>] [--out graph.json]`.
  - `--states` names an enum or string union declared in that file.
  - It reads three shapes:
    - transition tables (state → list of states, or state → {event: state});
    - named functions or methods that check the status field (`===`, `!==`, `[A,B].includes(x.status)`) and then set it (`x.status = S` or `status: S`), labelled with the function's name;
    - a `switch` on the field, with fall-through cases.
  - A function that sets the status without checking it first draws no edge and prints a warning.
  - It writes the graph through `checkGraph` from `skills/diagram/scripts/graph.mjs`.
- `skills/diagram/kinds/status-flow/scripts/check.mjs <graph.json> <rules.json>`: a breadth-first walk over (state, flags) from the start states.
  - Exit 0 prints "<n> rules hold".
  - Exit 1 prints one line per broken rule with the shortest path that breaks it.
  - Exit 2 means a bad graph or rules file.
  - Edges marked `removed` are not followed.
- `skills/diagram/kinds/status-flow/references/status-flow.md`: the kind's instructions.
- `skills/diagram/kinds/status-flow/references/rules-file.md`: the new rules-file format, with an example graph and an example rules file. Its fields:
  - `start`;
  - `flags` (each flag lists the states that set it);
  - `rules`, each with a `name`, an optional `says`, and either `never` (with optional `unless` flags) or `reach`.
- `skills/diagram/kinds/status-flow/package.json`: no dependencies.
- `skills/diagram/SKILL.md`: the kind's line is added under "Kinds".
- Tests and fixtures:
  - `tests/test_status_flow.py` (27 tests).
  - `tests/fixtures/diagram/status-flow/`: `keeps-rule.ts` and `breaks-rule.ts` (a fictional ticket workflow), `ticket-graph.json` and `rules.json`.
- The tests install `typescript@5` with pnpm into a cached temp folder (`$TMPDIR/jig-test-typescript-5`) and symlink it into each fixture repo's `node_modules`. They skip with a reason when Node or pnpm is missing or the install fails.
- Nothing domain-specific was copied from the statechart pilot.

**Acceptance criteria, as adjusted:**
1. **On a fixture state machine, the extractor writes a graph file the shared renderer draws.**
   - `ExtractTest.test_methods_become_edges_labelled_with_the_method` checks the exact graph.
   - `ExtractTest.test_extracted_graph_is_drawn_by_the_shared_renderer` runs `extract --out` then `render.mjs`, and checks the drawn edges.
   - Five more extraction tests cover the table, switch, `includes` and `--field` shapes, the warning, and refusing an unknown type.
2. **The breadth-first rules pass and fail, now on the graph file.**
   - `FixturePipelineTest.test_the_version_that_keeps_the_rule_passes` and `test_the_version_that_breaks_the_rule_fails_on_it` go from code to graph to check.
   - `CheckTest` (9 tests) covers the shortest path, flags, `reach`, `never` without `unless`, removed edges, and refusing unknown states and flags.
3. **The compiler comes from the `ast` lookup, with no `typescript` in the kind's `package.json`.**
   - All extraction tests use the fixture repo's local TypeScript, found through `ast_tool.py find typescript --repo <file's dir>`.
   - `CompilerLookupTest.test_no_compiler_in_the_repository_relays_the_lookup` expects exit 3.
   - `test_typescript_7_asks_for_a_typescript_5_path` expects exit 3 and a message asking for a TypeScript 5.x folder passed with `--typescript <path>`.
   - `test_a_typescript_5_path_is_used_in_a_typescript_7_repository` checks the override works.
   - `test_the_kind_bundles_no_typescript` checks the kind's `package.json`.
4. **A rules file in the documented format loads.** `DocsTest.test_the_documented_rules_file_loads_and_is_checked` takes both JSON blocks from `rules-file.md`, runs the check, and expects exit 0 with "3 rules hold".
5. **Nothing in the core points to `skills/status-flow`.** `DocsTest.test_nothing_in_the_core_points_to_the_old_status_flow_skill` greps the whole core, skipping `.git`, `node_modules`, worktrees and workflow-runs, and checks the folder doesn't exist. `DocsTest.test_the_diagram_skill_lists_the_kind` checks the line under "Kinds".

**Break table.** Each break was scripted, the test file run, and the file restored from a backup copy. A `diff -r` against the backups showed every file identical afterwards.

| Break | Tests that went red |
|---|---|
| E1 drop `!==` from the comparisons | methods_become_edges, renderer, ts5_path_in_ts7_repo, another_field, keeps_rule_passes |
| E2 ignore `[..].includes(field)` | list_of_allowed_states, breaks_rule_fails |
| E3 switch cases don't fall through | methods_become_edges, renderer, ts5_path_in_ts7_repo |
| E4 drop event tables | table_of_events_on_a_string_union |
| E5 drop list tables | table_of_allowed_states |
| E6 no warning for an unchecked set | status_set_without_a_check_is_warned |
| E7 ignore `--field` | another_field_name |
| E8 TypeScript 7 accepted | typescript_7_asks_for_a_typescript_5_path |
| E9 ignore `--typescript` | ts5_path_in_ts7_repo |
| E10 lookup failure exits 1 | no_compiler_relays_the_lookup, typescript_7_asks |
| E11 unknown type not refused | unknown_states_type_is_refused |
| E12 method names not used as labels | methods_become_edges, list_of_allowed_states, ts5_path_in_ts7_repo, another_field |
| E13 `--out` ignored | renderer, keeps_rule_passes, breaks_rule_fails |
| E14 nodes not in declaration order | methods_become_edges, table_of_events, ts5_path_in_ts7_repo |
| C1 flags not carried along a path | rules_hold, flag_set_earlier, removed_edges, documented_rules_file, keeps_rule_passes |
| C2 removed edges followed | removed_edges_are_not_followed |
| C3 last breach reported, not the shortest | shortest_breaking_path_is_reported |
| C4 reach rules never break | unreachable_state_breaks_a_reach_rule |
| C5 unknown states accepted | rule_naming_an_unknown_state_is_refused |
| C6 unknown flags accepted | unless_naming_an_unknown_flag_is_refused |
| C7 `unless` never excuses | rules_hold, flag_set_earlier, removed_edges, documented_rules_file, keeps_rule_passes |
| C8 start state sets no flags | flag_set_earlier |
| C9 `reach` keyword renamed | unreachable_state_breaks_a_reach_rule |
| C10 `says` left out of a broken line | broken_rule_named_with_shortest_path, flag_set_earlier, never_rule_without_unless, unreachable_state |
| C11 an empty `unless` excuses | never_rule_without_unless, shortest_breaking_path |
| C12 path shows ids, not labels | never_rule_without_unless |
| D1 SKILL.md drops the kind's line | diagram_skill_lists_the_kind |
| D2 GLOSSARY.md mentions `skills/status-flow` | nothing_in_the_core_points_to_the_old_status_flow_skill |
| D3 `typescript` added to the kind's `package.json` | the_kind_bundles_no_typescript |
| D4 doc example drifts (`reach` → `reachable`) | documented_rules_file_loads_and_is_checked |

Every one of the 27 tests went red under at least one break. The first D1 break (renaming the bold label) caught nothing because the test checks the paths, so it was redone as removing the line, which went red.

**Open or worked around, said plainly:**
- **Seams not confirmed with you:** the tdd skill asks for seams to be agreed with you before testing. As a subagent I took the ticket's acceptance criteria as the agreed seams: the `extract.mjs` CLI, the `check.mjs` CLI and the docs.
- **Not test-first throughout:** after the first test, which was red first, I wrote some extraction and lookup code ahead of its tests, so those tests passed on their first run. The break table shows each one catches a real break.
- **Extraction limits:** it is syntax-only within one file. The states type must be declared in the file being read, and conditions are not carried onto edges.
- **New convention for later kinds:** a kind keeps its instructions in `kinds/<kind>/references/<kind>.md`. Ticket #4 (the call-tree kind) may want to follow the same layout.
- **Temp folder left in place:** the break harness and backups are in /tmp/jig-1-8-3-breaks, outside the repository.

PASS
