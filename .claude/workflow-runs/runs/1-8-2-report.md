Ticket #2 (diagram skill) is built test-first and committed on `claude/1-8-2`. `drive.py checks 1-8 2` passes: 186 tests OK and the ratchet is ok. Merging `claude/1-8` reported "Already up to date". Nothing was pushed or merged elsewhere, and no issues were touched.

**Commit:** "Add the diagram skill: graph file, drawing and comparison"

**Files**
- `/Volumes/Development/personal/jig/.claude/worktrees/1-8-2/skills/diagram/SKILL.md` lists the scripts, has a "Kinds: none yet" section that tickets #3 and #4 add lines to, and the "No diagram kind covers this change" stop-and-ask. That section suggests a kind, points to the `ast` skill, offers the 3 choices and waits for the developer's pick.
- `.../skills/diagram/references/graph-file.md` documents the graph file format:
  - `title`, plus `groups`, `nodes` and `edges` lists.
  - Each item can have a `mark` (added, removed, unchanged or mismatch). It defaults to unchanged.
  - Edges are matched on their `from` and `to` pair. The same pair with a different label or mark counts as a changed edge.
- Scripts in `.../skills/diagram/scripts/`:
  - `graph.mjs` loads and validates the file and holds the shared colours and difference list.
  - `render.mjs <graph.json> <out.html>` draws the page with elkjs.
  - `compare.mjs <plan.json> <proof.json>` exits 0 when they match and 1 when they differ, printing lines such as `extra edge A -> B (label)`, `missing …` or `changed … : label x, now y`.
  - `mermaid.mjs <graph.json>` prints a fenced Mermaid flowchart.
  - All of them exit 2 on a bad graph file.
- `skills/diagram/package.json` and `pnpm-lock.yaml`: elkjs 0.12.2 is the only dependency.
- `.gitignore` now has `node_modules/`.
- `README.md` lists `compare.mjs` in its scripts table.
- Tests and fixtures: `tests/test_diagram.py` and `tests/fixtures/diagram/`. The fixtures are a generic document workflow (Draft, In review, Published, Archived).

**Design choice:** all scripts are Node (ESM), so the graph format is defined in one module, `graph.mjs`. Only `render.mjs` needs elkjs.

**Test setup:** I chose install-or-skip.
- Test classes that run the scripts install elkjs with `pnpm install --frozen-lockfile --dir skills/diagram` when it is missing.
- They skip with a clear reason if Node or pnpm is not there. `PackageTest` never skips.
- All tests ran. I deleted `node_modules` and confirmed the tests reinstall it with pnpm, then pass.
- With Node removed from PATH, 4 classes skip with "node is not installed: the diagram scripts need Node".

**Acceptance criteria**

| # | Criterion | Proof |
|---|---|---|
| 1 | Fixture renders to HTML with inline SVG and no `<script` or `http` | `RenderTest.test_page_has_inline_svg_and_nothing_external` runs the script on the fixture, checks the output, and parses the SVG to confirm the labels |
| 2 | Each of the four marks shows in its colour, and the difference list matches the graph | `test_each_mark_is_drawn_in_its_colour` and `test_difference_list_names_every_marked_item` on `all-marks.json` (one node and one edge in each state), plus `test_graph_with_no_marks_lists_no_differences` and `test_labels_are_escaped` |
| 3 | Identical graphs exit 0; an extra, missing or changed edge exits non-zero and names it | `CompareTest.test_identical_graphs_pass`, `test_extra_edge_fails_and_is_named`, `test_missing_edge_fails_and_is_named`, `test_changed_edge_fails_and_is_named` |
| 4 | Mermaid output matches the fixture | `MermaidTest.test_fixture_matches_its_snapshot` against the hand-written `all-marks.mermaid.md`, plus `test_quotes_in_labels_are_escaped` |
| 5 | Installs with pnpm, elkjs the only runtime dependency | `PackageTest.test_elkjs_is_the_only_dependency_and_pnpm_locks_it` |
| 6 | SKILL.md covers the stop-and-ask and stays short | Only my own read against `writing-for-agents` (about 30 lines, the format moved to a reference file, worded positively); not reviewed independently |

`GraphFileTest` also covers bad input: an edge to an unknown node, and an unknown mark.

**Break table** (every break was restored from a backup and checked identical to it)

| Break | Tests that went red |
|---|---|
| render: add a `<script>` tag | test_page_has_inline_svg_and_nothing_external |
| render: add svg xmlns (http) | test_page_has_inline_svg_and_nothing_external, test_each_mark_is_drawn_in_its_colour, test_labels_are_escaped |
| render: drop group labels | test_page_has_inline_svg_and_nothing_external |
| render: edges always grey | test_each_mark_is_drawn_in_its_colour |
| render: nodes always grey | test_each_mark_is_drawn_in_its_colour |
| graph: list includes unchanged items | test_difference_list_names_every_marked_item, test_graph_with_no_marks_lists_no_differences |
| render: drop "No differences." | test_graph_with_no_marks_lists_no_differences |
| render: no `<` escape | test_labels_are_escaped |
| compare: skip missing | test_missing_edge_fails_and_is_named |
| compare: skip extra | test_extra_edge_fails_and_is_named |
| compare: ignore edge label | test_changed_edge_fails_and_is_named |
| compare: always exit 0 | the extra, missing and changed edge tests |
| compare: every edge reported as changed | test_identical_graphs_pass plus the extra, missing and changed edge tests |
| mermaid: removed edge drawn solid | test_fixture_matches_its_snapshot |
| mermaid: no quote escape | test_quotes_in_labels_are_escaped |
| graph: allow unknown node | test_edge_to_an_unknown_node_is_refused |
| graph: allow unknown mark | test_unknown_mark_is_refused |
| package: add a devDependency | test_elkjs_is_the_only_dependency_and_pnpm_locks_it |

**Not done or still open**
- The tdd skill asks for seams to be confirmed with the user first. With no user to ask, I used the three script CLIs and `package.json` as the seams, because those are what the acceptance criteria name.
- The Mermaid output has not been checked by a Mermaid parser. The snapshot was written by hand to the flowchart syntax, but nobody has confirmed GitHub draws it. Doing so would need `mermaid-cli` (puppeteer and Chromium), which I didn't install.
- I didn't look at the rendered page in a browser, because the preview pane can't act on local files. I checked the layout coordinates instead: nodes sit inside their group box and edges end on node borders.
- `compare.mjs` only reports differences. It doesn't write a merged graph with mismatches marked; ticket #5 may want that.
- A hand-drawn graph is labelled through its `title`; there is no separate field for it.

ISSUES
