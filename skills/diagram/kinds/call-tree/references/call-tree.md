# Call tree

Draws every function one starting function reaches, across files, grouped by the file each is in. Back to [the skill](../../../SKILL.md).

## Get the compiler

The kind bundles no TypeScript and needs the full compiler, because following an import means resolving symbols across files. Get it the same way as the [status flow](../../status-flow/references/status-flow.md#get-the-compiler) kind: the `ast` lookup, or a TypeScript 5.x folder passed with `--typescript <path>` (exit 3 says which).

## Extract

```
node ~/.claude/skills/diagram/kinds/call-tree/scripts/extract.mjs <file.ts> --function <name> [--typescript <path>] [--out <graph.json>]
```

`--function` names a function, an arrow function held in a `const`, or a method as `Class.method`, declared in that file. The nearest `tsconfig.json` above the file sets the compiler options and the root that node ids are relative to; without one, the file's folder is the root.

- **Nodes**: each function reached, with the id `<file>#<name>` and the name as its label, in a group per file.
- **Packages**: a call into `node_modules` is a leaf in a group named after the package, and is not followed.
- **Left out**: the language's built-ins (`console.log`, `Array.map`), and calls the compiler can't resolve to a function with a body, such as a callback passed in as a parameter.
- **Recursion**: each function is followed once, so a cycle draws one edge each way and a function calling itself draws a loop edge.

Exit 2 means the file, the arguments or the function name don't hold together. Without `--out`, the graph file goes to stdout.

## Check a change

Extract from the same function before and after the change, then run the skill's `compare.mjs` on the two files: each call added or removed shows as one `extra` or `missing` edge.
