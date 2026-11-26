# Preferences

The core's default way of working, imported from `~/.claude/CLAUDE.md` by `install.sh`. A pack, a project's settings or its `CLAUDE.md` can override any line; the more specific one wins.

## Confirm before writing outside the conversation

Never write to an external system (an issue or ticket, a comment, a status change, a wiki page, a pull request, a chat message) without first asking and getting an explicit yes for that action. This holds even when the request says "create", "post", "raise" or "send", because it often means "draft it for me". Draft the content in chat, show it, and ask whether to create or post it. Read-only lookups need no yes. The outbound-guard hook asks for the same yes.

## Plans the developer can read at a glance

A plan says what will change in plain words, one row per change with its reason, real decisions only, tests per acceptance criterion, one line for everything checked that needs nothing, and questions last. Size it to the change: a wording fix or one-line fix gets a one- or two-line plan; new data or infrastructure gets the full shape. Show conclusions, not the working. Flag any build change the plan didn't list before making it. A plan the developer can't read at a glance can't be checked, so wrong or unneeded changes get approved.

## Simple code and minimal infrastructure

Prefer modular code that is easy to change, and the smallest infrastructure change that works now, with one line on how it would grow. Map every new field, status, table, index or resource to a current read or write, and rule out an existing one first; reuse an existing status before adding a parallel field; leave indexes and attributes until something needs them. The rules are in `codebase-design`'s "Simple and easy to change" section.

## Suggesting tools

When suggesting a tool, library or service the developer hasn't named, offer two to four, each with one line on what it is and its trade-off, and let the developer pick. Never introduce one by name alone.

## pnpm for Node

Use pnpm for Node work, unless the repository already has another package manager's lockfile.

## The environment over memory

Anything that can be proven is proven by the environment, not held in memory. If code or a live system can prove a fact, a script derives it on demand. If a mistake can be caught mechanically, a hook or check enforces the rule. Memory keeps only what nothing can prove: preferences, agreements, decisions with their reasons, and plans or dates not yet recorded anywhere. Before saving a memory, ask whether a script could derive it, and propose the script instead. Keep documentation to the least that does the job, and delete prose once a script or check takes over its rule. A memory goes stale without anyone noticing and costs context on every load; a script or check stays correct. When a step has no script or skill that covers it, say so before doing it by hand and suggest the script that would: improvising silently hides the gap and can drift off task.

## Commit messages

A short title, then one to four short bullets that start with a verb ("- Adds…", "- Passes…", "- Caps…"). No paragraphs and no explanation of why. If unsure, read the developer's last few commits in the repository (`git log --author=<developer> -5`) and match them.

## Rebase rather than merge

When bringing a branch up to date or clearing conflicts, rebase onto the main branch (`git rebase origin/main`) and push with `--force-with-lease`, after confirming the push. Fall back to a merge only when a rebase isn't practical, and say why. On someone else's pull request, flag the conflict to its author rather than pushing. The git-guard hook asks before a merge of main and denies a plain force push.
