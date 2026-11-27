# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root: the terms Jig uses.
- **`docs/decisions.md`**: the decisions that shape Jig, one `###` section each with its reason. Read the ones that touch the area you're about to work in.

Jig is single-context: one glossary and one decisions file. It keeps its decisions in one file, not a `docs/adr/` folder, so add a new decision as a section in `docs/decisions.md`.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag decision conflicts

If your output contradicts a decision in `docs/decisions.md`, surface it explicitly rather than silently overriding:

> _Contradicts "The core holds no organisation's facts", but worth reopening because…_
