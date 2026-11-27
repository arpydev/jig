---
name: diagram
description: Draw a graph file as a diagram, check a proof diagram against its plan diagram, or write a graph as Mermaid for a pull request. Use when a task needs a plan or proof diagram, or the developer asks to see a change as a diagram.
---

# Diagram

A diagram kind's extractor reads the code and writes a graph file ([format](references/graph-file.md)). The scripts below draw and check any graph file, whatever its kind.

Install once with `pnpm install --dir ~/.claude/skills/diagram`. Only drawing needs it.

## Kinds

Each kind adds a line here: what it draws and the command that extracts its graph file.

- **Status flow** ([how to use it](kinds/status-flow/references/status-flow.md)): a TypeScript state machine's states and transitions, checked against a rules file. Extract with `node ~/.claude/skills/diagram/kinds/status-flow/scripts/extract.mjs <file.ts> --states <type>`.

## Scripts

- **Draw**: `node ~/.claude/skills/diagram/scripts/render.mjs <graph.json> <out.html>` writes one self-contained HTML page with the diagram and the list of differences under it. Open it in the file panel.
- **Check**: `node ~/.claude/skills/diagram/scripts/compare.mjs <plan.json> <proof.json>` exits 0 when the proof graph matches the plan graph, and 1 with one line per missing, extra or changed group, node or edge.
- **Pull request**: `node ~/.claude/skills/diagram/scripts/mermaid.mjs <graph.json>` prints a Mermaid block to paste into the body, which GitHub draws.

Every script exits 2 and names the problem when a graph file doesn't hold together.

## When no kind covers the change

Stop and tell the developer "No diagram kind covers this change". Suggest the kind that would: what it would read, and which AST tool it needs (the `ast` skill finds or picks one). Then offer three choices and wait for the developer's pick:

1. Add the kind first (the usual choice).
2. Hand-draw the graph file once, with the title "hand-drawn, not extracted".
3. Go without a diagram.
