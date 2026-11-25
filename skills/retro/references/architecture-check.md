# Architecture check

A short look for deepening opportunities in the code a run touched, based on Matt Pocock's `improve-codebase-architecture`. It isn't a codebase-wide review. The goal is to notice friction while it's fresh and turn anything worth fixing into a tech-debt ticket.

Run it in the retro only when the diff changes a module's shape: it adds or changes a service, adapter, port or domain type's interface, or adds infrastructure such as a table, index, queue, function or permission grant. Skip it when the changes stay inside existing functions or components, or are only config, copy or tests. Those rarely produce a deepening candidate, and the check costs a fresh agent that re-reads the diff. When unsure, say which way you chose in the retro and let the developer decide.

## Scope

Only the files in the run's diff, plus the modules they call or are called by directly. This includes infrastructure code: tables, indexes, queues, functions and permission grants the diff adds or touches. Note which of these files keep coming up in recent history (`git log --oneline -30 -- <path>`), because deepening pays back most where code changes often.

## Run it in a fresh agent

Start a new `general-purpose` agent with no context from the run, so it judges the code rather than Claude's reasons for writing it. Give it:

- the repo path and the list of files in scope;
- the instruction to load the `codebase-design` skill and use its vocabulary (module, interface, depth, seam, adapter, leverage, locality) and the deletion test;
- the repo's pattern docs (the `retro` step additions name them) and the note that they win over `codebase-design`;
- the local glossary and ADRs (see the `domain-modeling` skill for where they are), with the note that an ADR's decision isn't reopened unless the friction is serious;
- the instruction to apply the skill's "Simple and easy to change" section, looking for duplicate state (two fields for one fact), and for indexes, fields, resources or grants that nothing reads;
- the ask: "Read only. Report at most three deepening or simplifying candidates in the code and infrastructure in scope. For each: the files, the problem (why it causes friction now), the change in plain words, what gets easier to test or change, and a strength of Strong, Worth exploring or Speculative. 'Nothing worth changing' is a good answer. No interface designs yet. Under 400 words."

## Present the result

Show the candidates in the retro alongside the friction candidates, using the agent's words. Mark each one **ours** (this run made it worse) or **existing**. Then:

- **Strong:** offer to draft a tech-debt issue in the project's tracker (the `tickets` step additions name its ticket-writing skill, if any). First search the tracker for an open issue about the same area, and add to that issue instead of making a new one. Show the draft and create it only after the developer approves.
- **Worth exploring:** record it in the run's retro outcome. If the same area comes up again in a later run, treat that as Strong.
- **Speculative:** mention it in one line, or drop it.
- **Rejected by the developer for a lasting reason:** offer a local ADR (see `domain-modeling`) so later checks don't suggest it again.

A finding that is ours and small enough to fix in the current branch goes back to the developer as a choice to fix it now, not as a ticket.
