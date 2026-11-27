---
name: ast
description: Find the AST tool for a language so code structure is read as a syntax tree. Use before answering a structural question (who calls a function, what a module imports, which statuses exist) or drawing a diagram from the code.
---

# AST

A structural question answered from a syntax tree is exact; grep only guesses. The developer chooses each language's AST tool, and the core bundles no parsers.

## Find the tool

Run `python3 ~/.claude/skills/ast/scripts/ast_tool.py find <language>` from inside the repository. It returns the tool saved as `ast.<language>` in the project settings; with nothing saved, it looks for the repository's own tool (such as `node_modules/typescript`).

- **Exit 0**: use the tool it prints.
- **Exit 2**: several tools are installed and none is saved. Show the developer the list it prints, ask which to use, and save their pick.
- **Exit 3**: none is installed or saved. Suggest candidates, ask the developer to pick one, and save their pick.

The developer always picks: with several tools or none, ask rather than choosing one yourself.

## Suggest candidates

Suggest two to four, from different ecosystems where the language allows (the language's own compiler API, a tree-sitter grammar, a standalone parser library). Each suggestion gets one line saying:

- what it is;
- its trade-off (speed, install size, how well it keeps up with the language);
- whether it resolves symbols across files. A call tree or dependency graph needs that; a syntax-only parser can't follow an import.

Installing the pick is the developer's call. For a Node package, use pnpm unless the repository has another package manager's lockfile.

## Save the pick

Run `python3 ~/.claude/skills/ast/scripts/ast_tool.py save <language> <tool>`, where `<tool>` is the path or command the developer chose. It writes `ast.<language>` to the project settings, so the next `find` returns it and the question is asked once per repository. With no project settings, it says to run the `setup-workflow` skill first.
