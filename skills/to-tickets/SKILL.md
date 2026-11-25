---
name: to-tickets
description: Break a spec, plan, epic or the current conversation into tracer-bullet tickets split so as many as possible can run in parallel, each declaring its blocking edges, published to the configured tracker (edges as text in one file per ticket locally, or native blocking links on a real tracker). Use when the developer says "break down this epic", "split this into tickets", "plan the tickets", "re-split this epic", or asks why the work ended up with blockers.
---

<!-- Local fork of mattpocock/skills to-tickets (MIT, see ../../LICENSE-mattpocock-skills), merged with the developer's own epic splitting method. upstream/ holds the version it was taken from. Every local change is listed under "Local changes" at the end. -->

# To Tickets

Break a plan, spec, or conversation into a set of **tickets**: tracer-bullet vertical slices, each declaring the tickets that **block** it. Goal: logically cohesive tickets (work that makes sense to do together), split so as many as possible can start at the same time.

The issue tracker and triage label vocabulary should have been provided to you. If not, tell the user to run `/setup-workflow`.

Before step 1, run `python3 ~/.claude/skills/setup-workflow/scripts/settings.py steps tickets`. Read each file it prints and load each `skill:<name>`. They add the project's ticket layout, sizes and tracker steps, and they win over this skill where they disagree.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments.

If the source wasn't grilled in this conversation (an epic or issue written elsewhere), grill the developer on it before listing its work: load the `grilling` skill, and the `domain-modeling` skill so the terms are settled in the glossary before they spread into ticket text. Ask about scope (what now, what later), the main decisions and the names of new things (statuses, lists, records). Stop when nothing is left silently assumed, summarise, and get it confirmed before step 3.

Find anything the work depends on from other teams or outside parties. If the technical approach has an unknown that changes how the work splits, propose a spike first and say what it needs to answer.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. List what the work needs, not the screens in the order a user sees them

Group the work by kind:

- **Data**: tables, indexes, new fields.
- **Behaviour**: endpoints, status rules, events, scheduled jobs.
- **Screens**: pages, lists, forms, changes to existing pages.
- **Integrations**: other teams' services, outside parties, downstream systems.

Splitting by user journey (list, then details, then form, then the form's outcomes) puts every page behind the page that links to it, so the tickets end up in one long chain.

### 4. Separate out the foundations

The foundations are the work everything else needs: infra tables, the feature flag, and the core flow that creates the work's main records, plus any prefactoring. Keep this set as small as possible, because everything else waits on it.

Check every table, index, field and status the foundations add against "Simple and easy to change" in the `codebase-design` skill. List the work's reads and writes, map each to an existing table, key or index, and add only what nothing existing can serve. Settle the table keys carefully, because they're hard to change. Leave secondary indexes and extra attributes until a ticket needs them, and write one line on how each table would grow.

### 5. Draft vertical slices

Break the work into **tracer bullet** tickets.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests): vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

Give each ticket its **blocking edges**: the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

When slices would wait on each other, cut along boundaries that let tickets run at the same time:

- **Backend and UI** meet at an agreed contract: the endpoint's request and response shape, written on both tickets. Backend work that doesn't need a page can start as soon as its data exists.
- **Each page gets its own route**, so it doesn't depend on the page that links to it. Whichever ticket lands second adds the link.
- **Work for another team or an outside party** gets its own ticket in their backlog, agreed with them before dependent tickets are called ready.
- **Behind a feature flag, a ticket doesn't need anything users can see.** Users see nothing until the flag is on, so slicing by screen only adds waiting. Choose the split that lets more people work at once.
- **Shared components** (cards, forms reused on more than one page) are named on the ticket that builds them and on the tickets that reuse them.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change (rename a column, retype a shared symbol) whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket; green is promised only there.

### 6. Size each ticket

- **Too small:** it can't be tested on its own, it's a one-line change, or it only exists to hand over to the next ticket. Merge it into a neighbour.
- **Big is fine when it's cohesive.** A ticket with many ACs, or one that covers backend work and a screen, stays whole when its parts change the same files or one part needs another. Split it only where there's a clean line: a piece that makes sense on its own, shares no files with the rest and doesn't wait on it. If there's no clean line, keep it whole and say why. Two people would end up pairing on it anyway.
- **Very large work can still be split with a blocker.** When a ticket is too big for one person, or for one fresh context window, split it into cohesive pieces even if one blocks another. Add the blocking edge and say on the ticket why the blocker is accepted. Aim for parallel tickets first. A known blocker is the exception, and step 8's longest-chain check still applies.
- Put **variations of one action** (the outcomes of one endpoint, the options on one form) in one ticket if it still fits. Separate tickets that change the same code can't run in parallel and will conflict.

### 7. Decide what kind each dependency is before linking it

For each "this needs that", ask what the need really is:

| Kind | Meaning | What to do |
|---|---|---|
| Code | The ticket calls, extends or renders something the other ticket builds | Add a blocking edge |
| Navigation | The ticket is only reached through the other ticket's page | Add a note; give the page its own route |
| Test data | The ticket only needs records the other ticket creates | Add a seed step, fixture or dev tool to the ticket's test data; no edge |
| Contract | The ticket needs the shape of something the other ticket builds, not the thing itself | Agree the shape on both; no edge |

Only code dependencies block.

### 8. Check the dependency graph

- **Longest chain:** after the foundations, the longest chain of blocked tickets should be three or fewer. If it's longer, re-split, or say why it can't be shorter.
- **Width:** count how many tickets can start once the foundations are done. It should be at least the number of people, or implementer agents (`implementers` in the settings), likely to work on it.
- **Overlap:** tickets that can run at the same time shouldn't change the same files. Flag any two tickets with no blocking edge between them that are likely to touch the same area. Worked in parallel, they conflict on merge and one can silently drop the other's work. Merge them, or put them in order on purpose and say why.
- **Flag removal:** the last ticket removes the flag. It's blocked by the tickets that complete the feature, and shouldn't count towards the longest chain.

### 9. Quiz the user

Show the plan before the drafts. Keep it readable: lead with what the work will deliver in a few plain sentences, then the foundations, then the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Kind**: backend, UI, infra or integration
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work
- **Why**: the user story or decision it serves, in one line
- **Likely to touch**: the feature folders, tables and shared components it will change, each area with its folder

Then the dependency graph: what can start after the foundations, the longest chain, and any dependency kept on purpose with its reason. Then anything that needs another team, an outside party or a spike. Put questions last, with a recommendation each.

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct: does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown. Then draft each ticket in full, and show the drafts before publishing anything.

### 10. Publish the tickets to the configured tracker

Publish the approved tickets. **How** depends on the tracker `/setup-workflow` configured; the tickets are the same either way, only the shape of the blocking edges changes:

- **Local files** → write one file per ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order (blockers first). Each file's "Blocked by" lists the numbers/titles it depends on. Use the per-ticket file template below: one ticket per file, never a single combined file.
- **A real issue tracker (GitHub, Linear, …)** → publish one issue per ticket in dependency order (blockers first) so each ticket's blocking edges can reference real identifiers. Use the platform's native blocking relationship where it has one; otherwise set each ticket's "Blocked by" to the blocking issues. If the source was an existing issue, make each ticket its sub-issue (tracker doc's operation). Apply the `ready-for-agent` triage label unless instructed otherwise; the tickets are agent-grabbable by construction.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

Do NOT close or modify any parent issue.

<local-ticket-template>

# <NN>: <Ticket title>

**What to build:** the end-to-end behaviour this ticket makes work, from the user's perspective, not a layer-by-layer implementation list.

**Why:** the user story or decision it serves, in one line.

**Blocked by:** the numbers/titles of the tickets that gate this one, or "None (can start immediately)".

**Status:** ready-for-agent

- [ ] Acceptance criterion 1 → test: what proves it, at which seam
- [ ] Acceptance criterion 2 → test: what proves it, at which seam

**Test data needed:** the seeds, fixtures or records the tests need, or "None".

**Likely to touch:** each area with its folder, such as "workout logging (`src/features/workouts`)".

</local-ticket-template>

<issue-template>

## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective, not layer-by-layer implementation.

## Why

The user story or decision it serves, in one line.

## Acceptance criteria

- [ ] Criterion 1 → test: what proves it, at which seam
- [ ] Criterion 2 → test: what proves it, at which seam

## Test data needed

The seeds, fixtures or records the tests need, or "None".

## Blocked by

- A reference to each blocking ticket, or "None (can start immediately)". Omit this section when blockers were set as native edges.

## Likely to touch

- Each feature folder, table and shared component as an area followed by its folder in backticks, from the repository root, such as "workout logging (`src/features/workouts`)", so `/implement-spec` can avoid running overlapping tickets at the same time. Name folders, never files; for a folder that doesn't exist yet, name its parent.

</issue-template>

In either form, avoid specific file paths or code snippets: they go stale fast. "Likely to touch" names folders rather than files for the same reason. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Re-splitting work already in progress

Leave tickets that have started (in progress, in review, done) alone; the project's step additions name its statuses. Re-split only what hasn't started. Turning navigation and test-data links into notes is often enough to unblock tickets without rewriting them. Ask before changing tickets someone else has refined.

## Local changes

Taken 2026-11-23 from github.com/mattpocock/skills at commit abeeaf9 (`skills/engineering/to-tickets/`, MIT licence), first into another project and moved to the core on 2026-11-25. When upstream changes, diff it against `upstream/`, carry the changes in, keep the changes below, then replace `upstream/`.

| Date | Change | Why | Upstream? |
|---|---|---|---|
| 2026-11-23 | Each ticket gets "Likely to touch", and the breakdown flags unblocked tickets that overlap (from another project's "usage savings") | Parallel tickets on the same area conflict on merge and can drop each other's work | Local only |
| 2026-11-24 | Points at `/setup-workflow`, not `/setup-matt-pocock-skills` | `setup-workflow` took over writing `docs/agents/*.md` | Local only |
| 2026-11-25 | Merged with the developer's own epic splitting method: grill an ungrilled source, work by kind, foundations, parallel cuts, sizing, dependency kinds, graph check, plan before drafts, re-splitting. Model-invocable with its trigger phrases | One skill for splitting work into tickets in every project; company parts are a pack's `tickets` step addition | Local only |
| 2026-11-25 | Runs `settings.py steps tickets` for its step additions | Packs and projects add their rules without changing the core | Local only |
| 2026-11-25 | Each ticket carries a "Why" line, a test per AC and the test data needed | The tickets are the plan in spec to PR, and these were the gaps against a pack's delivery plan | Propose upstream |
| 2026-11-25 | "Likely to touch" names each area's folder | `drive.py` matches touches as paths, so areas alone ran every ticket alone | Local only |
