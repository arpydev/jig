Fix for ticket #2 (run 1-8), worktree /Volumes/Development/personal/jig/.claude/worktrees/1-8-2, branch `claude/1-8-2`. The branch was confirmed before any work started.

**Result: the real Mermaid parser accepts the writer's output, so I changed no code.**

**How I parsed it**
- Installed `mermaid@12.3.0` and `jsdom@31.0.1` with `pnpm add` into a temporary folder outside the repo, `/tmp/mmd-parse-1-8-2`. The folder is deleted now, and `skills/diagram/package.json` is unchanged.
- A small Node script set up a jsdom window. For each file it removed the ```` ```mermaid ```` fence, called `mermaid.parse(text)`, then called `mermaid.mermaidAPI.getDiagramFromText(text)` and printed what the flowchart parser recorded.
- Inputs:
  - `node skills/diagram/scripts/mermaid.mjs tests/fixtures/diagram/all-marks.json`. Its output matches the snapshot `all-marks.mermaid.md` exactly (`diff` printed nothing).
  - A quotes case: node `Say "hi"` with an edge labelled `x "y"`.

Output:
```
OK all-marks.md: flowchart-v2 vertices=4 edges=4 subgraphs=1 subgraphClasses=[["g0",["unchanged"]]] vertexClasses=[["n0",["unchanged"]],["n1",["added"]],["n2",["mismatch"]],["n3",["removed"]]] edgeStyles=[["stroke:#2e7d32","fill:none"],["stroke:#ef8f00","fill:none"],["stroke:#757575","fill:none"],["stroke:#c62828","fill:none"]] edgeTypes=["normal","normal","normal","dotted"]
OK quoted.md: flowchart-v2 vertices=2 edges=1 subgraphs=0 ... edgeStyles=[["stroke:#757575","fill:none"]]
{"nodes":["Draft","In review","Published","Archived"],"groups":[["Editing",["n0","n1"]]],"edges":[["n0","n1","submit"],["n1","n2","approve"],["n0","n2","publish"],["n2","n3",""]]}
{"nodes":["Say ﬂ°quot¶ßhiﬂ°quot¶ß","b"],"groups":[],"edges":[["n0","n1","x ﬂ°quot¶ßyﬂ°quot¶ß"]]}
```
- **`class g0 unchanged` on a subgraph** is accepted. The parser puts the class on subgraph g0.
- **`linkStyle 0..3`** is accepted. Each line applies its stroke to the right edge. The parser checks `linkStyle` indexes against the edge count, so this also confirms all four edges were seen.
- **Edge forms** are accepted. `-->|"label"|` parses as a normal edge with its label, and `-.->` parses as a dotted edge.
- **Nodes, groups and edge labels** come out the same as in `all-marks.json`.
- **`#quot;`** is Mermaid's own entity syntax. The parser stores it as its internal placeholder (the odd characters in the output above) and turns it back into `"` when drawing.

**Negative controls**, to show the parser can fail:
- `linkStyle 3` on a graph with no edges failed with "Cannot set properties of undefined (setting 'style')".
- An unclosed `n0["a" -->` failed with "Parse error on line 4".
- The parse script exited 1 on these.

**What changed:** nothing. `mermaid.mjs` and the snapshot were already valid, so there was no failing test to write first and no new break-table rows. I didn't commit, because there was nothing to commit. The branch head is still 5309dcb.

**Parser left out of the test suite.** It would need mermaid and jsdom, which are tens of MB and many packages, installed on every test machine. It would also have to live outside `package.json`, which must list only elkjs. The parse output above is the one-off proof.

**Merge and checks**
- `git merge claude/1-8` printed "Already up to date".
- `python3 ~/.claude/skills/implement-spec/scripts/drive.py checks 1-8 2` passed: 186 tests OK. The log is at /Volumes/Development/personal/jig/.claude/workflow-runs/runs/1-8-checks-2.log.

**Still open (left alone as asked)**
- There is no merged-graph writer.
- GitHub's own drawing hasn't been seen. GitHub may run an older Mermaid than 12.3.0, but `subgraph`, `class`, `classDef`, `linkStyle`, `-->|..|` and `-.->` all date from Mermaid 8 or 9.
- The SKILL.md `writing-for-agents` review is still only the implementer's own.

PASS
