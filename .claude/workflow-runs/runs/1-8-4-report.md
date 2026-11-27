## Ticket #4: TypeScript call-tree diagram kind

All four acceptance criteria are met and the drive checks pass. The work is one commit on `claude/1-8-4`: `a853d1a`. Merging `claude/1-8` into it said "Already up to date". `drive.py checks 1-8 4` ran 227 tests, all OK, and the ratchet passed (log: `/Volumes/Development/personal/jig/.claude/workflow-runs/runs/1-8-checks-4.log`).

### What was built
- **The kind**: `skills/diagram/kinds/call-tree/` holds `scripts/extract.mjs`, `references/call-tree.md`, and a `package.json` with no dependencies.
  - Command: `extract.mjs <file.ts> --function <name | Class.method> [--typescript <path>] [--out <graph.json>]`.
  - It builds a TypeScript program from the nearest `tsconfig.json`, or from defaults if there is none. It uses the type checker to resolve imports across files.
  - It walks breadth-first from the starting function, following each function once.
  - Node ids are `<file relative to root>#<name>`, with one group per file.
  - A call into `node_modules` becomes a leaf in a group named `<pkg> (package)` and is not followed.
  - Calls into the language's built-ins (`console.log`, `.map`) are left out.
- **Shared compiler lookup**: the lookup moved out of status-flow into `skills/diagram/scripts/typescript.mjs` (`typescriptFor`, `runKind`). Both kinds now use it. Status-flow behaves the same: its 26 tests pass unchanged.
- **SKILL.md**: the Kinds section of `skills/diagram/SKILL.md` has a Call tree line.
- **Fixture**: `tests/fixtures/diagram/call-tree/` contains:
  - `project/` with three files (`main.ts`, `orders.ts`, `pricing.ts`). They include a method, functions nothing reaches, and the pair `expandTree` ↔ `walkTree` calling each other across two files.
  - `packages/tiny-format/`, which the tests copy into the temporary `node_modules`. It can't live in the repo under that name because the repo's `.gitignore` ignores `node_modules/`.
  - `after/main.ts`, which adds one call, and `main-graph.json`, the hand-written expected graph.
- **Tests**: `tests/test_call_tree.py`. They reuse `typescript5()`, `needs_node()`, `run()` and `read_json()` from `test_status_flow.py`. That means a cached TypeScript 5 installed with pnpm, and skipping when Node or pnpm is missing.

### Acceptance criteria
1. **Every function reached across files, and no others**: `test_every_function_reached_across_files_and_no_others` and `test_the_graph_matches_the_worked_example`, on the three-file fixture.
2. **A package call is a leaf, not followed**: `test_a_call_into_a_package_is_a_leaf_in_the_package_group` and `test_a_package_function_is_not_followed_into_its_own_calls`. The second gives the package a real body whose own call must stay out of the graph.
3. **Recursion and cycles end**: `test_mutual_recursion_across_files_ends_with_one_edge_each_way` and `test_a_function_calling_itself_ends_with_a_loop_edge`. Each extract run has a 60-second timeout, so a loop fails the test instead of hanging it.
4. **One added call shows as one added edge**: `test_one_added_call_is_one_extra_edge`. It extracts before and after into files and runs `compare.mjs` on them, which must exit 1 with exactly `extra edge main -> expandTree\n`.

Other tests: entry as `Class.method`, an arrow function held in a `const`, an unknown function name exits 2, `--out` writes the file, the shared lookup's exit 3 and TypeScript 7 → pass a 5.x folder path rule, the kind bundles no TypeScript, and the Kinds line is in SKILL.md.

### Break table
Each break was made by a script, then the file was restored from a backup and compared byte for byte.

| Break | Tests that went red |
|---|---|
| Follow calls inside packages | a_package_function_is_not_followed |
| Treat node_modules files as project files | package_leaf, not_followed, every_function_reached, worked_example, out_writes |
| No visited check (re-queue every callee) | mutual_recursion fails with "extract.mjs ran for 60s: the call tree never ended". Before the timeout was added, the suite hung; it was then rerun on its own and went red. |
| Don't resolve import aliases | package_leaf, not_followed, arrow_const, every_function_reached, mutual_recursion, one_added_call (comparison), out_writes, worked_example |
| Keep built-in library calls | method_entry, arrow_const, every_function_reached, out_writes, worked_example |
| Drop the class from method names | method_entry, arrow_const, every_function_reached, out_writes, worked_example |
| Ignore arrow functions held in a const | arrow_const |
| Only the first call in each function | package_leaf, not_followed, arrow_const, every_function_reached, one_added_call, out_writes, worked_example |
| Drop self-loop edges | function_calling_itself |
| Unknown entry not refused by name | unknown_entry_refused |
| `--out` ignored | one_added_call, out_writes |
| `--typescript` ignored | ts7 test in both kinds (call-tree and status-flow) |
| Lookup failure exits 2, not 3 | no_compiler test in call-tree, ts7 test in status-flow |
| Kind bundles typescript | kind_bundles_no_typescript |
| Kinds line link removed from SKILL.md | diagram_skill_lists_the_kind |
| Package group label without "(package)" | out_writes, worked_example |

Every new test went red under at least one break.

### Open points
- **Seams not confirmed with you**: as a subagent I couldn't ask. I tested at the CLI (`extract.mjs`, plus `compare.mjs` for the comparison) as the only public interface, the same way status-flow's tests do.
- **Commit trailer**: the commit ends with the `Co-Authored-By` line from the session attribution. The "no co-author line" rule in memory is specific to a work repository, so I didn't apply it here. Drop the line if you don't want it in Jig.
- **Not handled yet**: `new X()` constructor calls are not drawn as calls. Callbacks passed in as parameters and other calls the compiler can't resolve are left out; the reference says so.

PASS
