---
name: knowledge-map
description: The developer's evidence-backed map of how well they know each area of a project, which sets how much to explain and when to check their understanding. Use before explaining findings or code in an area, before drafting text that goes out under the developer's name (test notes, tickets, tech-debt tickets, docs, PR descriptions), when grilling reaches its knowledge check, or when the developer explains something back or catches a mistake.
---

# Knowledge map

The developer signs off what Claude finds and drafts. They can only check it if they understand it, and text that goes out under their name has to be text they could defend without Claude. The map records, per area of a project, how well the developer knows it, backed by dated evidence. It is a **ratchet**: a level rises only on evidence, and an area whose evidence has gone stale comes back up for a re-check, even one the developer built.

`scripts/knowledge.py` (relative to this skill's folder) owns the map at `~/.claude/knowledge/<project>.md`, outside every repository:

- `knowledge.py status [PATH ...]`: for the areas covering these paths, the level, last evidence, and whether to explain first. Paths no area covers are listed as new.
- `knowledge.py record AREA --level LEVEL --evidence TEXT [--paths a,b]`: add a dated evidence line and set the level. A new area needs `--paths` (folder or file prefixes).

Levels: **new**, **followed it**, **can explain**, **can teach**. An area is **re-check due** when its newest evidence is over 90 days old or its paths have had 20 commits since; the script works that out from git on every run.

## Working in an area

Run `status` with the paths the work touches before explaining findings, proposing changes or drafting anything. Then, per area:

- **new** or **followed it**, or **re-check due**: explain from the user's side first. Say who reaches this code, doing what, and how often, then trace the path from their action to the code, then the change. Before acting on it, ask one explain-back question the developer can answer only if they followed, and wait for their answer. Correct what they got wrong and ask again rather than carrying on.
- **can explain**: work as normal; explain only what is new to the area.
- **can teach**: be brief.

When the developer wants to learn an area properly rather than get a task done, point them to `/teach`.

## Before text goes out under the developer's name

For an area below **can explain** or re-check due, put the matching question to the developer before drafting is final, and let their answer shape the text:

- **Test notes**: for each step, what would fail if the feature were removed? A step with no answer is not testing the feature.
- **Tech-debt or bug tickets**: how does a real user or system reach this state? Name the code path or a data count. No reachable path, no ticket.
- **Documentation**: could you explain this section to a colleague without the doc in front of you?

The outbound guard backs this up with a warning when outgoing text names such an area. It warns; it never blocks.

## Recording evidence

Evidence is something the developer showed, not something they agreed to:

- answered an explain-back question correctly before being given the answer
- explained the area, or a change in it, in their own words
- caught Claude being wrong about it
- built or changed it and then explained it back (building alone is not evidence)

"Looks good" or approving a summary is not evidence. When the developer shows evidence, propose one line: the area, the level it supports, the date and what they showed. Record it only when they say yes; the developer moves the level, and may move it down too. Keep each line about the developer's own understanding: no one else's name or words, and no customer or patient data.
