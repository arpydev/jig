# Status flow

Draws a TypeScript state machine as states joined by the transitions the code allows, and checks it against a rules file. Back to [the skill](../../../SKILL.md).

## Get the compiler

The kind bundles no TypeScript. `extract.mjs` runs `python3 ~/.claude/skills/ast/scripts/ast_tool.py find typescript` for the repository the file is in, and uses the compiler it prints.

- **Exit 3 from the lookup**: none or several compilers are installed. Follow the `ast` skill: ask the developer, save their pick, run again.
- **Exit 3 naming TypeScript 7**: TypeScript 7 has no stable JS API. Ask the developer for a TypeScript 5.x folder; if they have none, suggest `pnpm add typescript@5 --dir <temp folder>`. Pass it with `--typescript <path>/node_modules/typescript`.
- **Exit 3 naming another tool** (such as `ts-morph` saved as the pick): pass a TypeScript 5.x folder with `--typescript <path>` the same way.

## Extract

```
node ~/.claude/skills/diagram/kinds/status-flow/scripts/extract.mjs <file.ts> --states <type> [--field status] [--typescript <path>] [--out <graph.json>]
```

`--states` names an enum or a union of string literals declared in that file; its members become the nodes, in declaration order. Transitions come from three shapes in the file:

- **A transition table**: an object literal keyed by states. Each value is either a list of states (unlabelled edges) or an object of events to states (edges labelled with the event).
- **A function that checks, then sets**: inside a named function or method, comparisons of the field with a state (`===`, `!==`, `[A, B].includes(x.status)`) are the from-states, and assignments of a state to the field (`x.status = S`, or `status: S` in an object literal) are the to-states. Each pair is an edge labelled with the function's name.
- **A switch on the field**: each case's states lead to the states its statements set. Empty cases fall through to the next.

`--field` names the field holding the state (default `status`). A function that sets the field without checking it first draws nothing and prints a warning on stderr: read that function and say what it means to the developer. Exit 2 means the file or arguments don't hold together.

Without `--out`, the graph file goes to stdout. Draw, compare or turn it into Mermaid with the skill's scripts.

## Check

```
node ~/.claude/skills/diagram/kinds/status-flow/scripts/check.mjs <graph.json> <rules.json>
```

The developer decides the rules: which states an item starts in, which facts a path picks up, and what must or must never happen. Write them in a [rules file](rules-file.md) next to the code it describes. A broken rule prints the shortest path that breaks it; show the developer that path with the line of code behind each step.
