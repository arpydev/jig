---
name: grilling
description: Grill the developer relentlessly about a plan, decision, ticket or idea until there is a shared understanding with nothing silently assumed. Use when the developer wants to stress-test their thinking, uses any 'grill' trigger phrase, or another skill reaches its grill step.
---

<!-- Local fork of mattpocock/skills grilling (MIT, see ../../LICENSE-mattpocock-skills). upstream/ holds the version it was taken from. -->

# Grilling

Interview the developer relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it. The aim is a shared understanding with nothing silently assumed, the way a sharp reviewer would interview in refinement.

## Step additions

Before the first question, run `python3 ~/.claude/skills/setup-workflow/scripts/settings.py steps grill`. Read each file it prints and load each `skill:<name>`. They add the questions and lookups that matter in this project, and they win over this skill where they disagree.

## Before the first question

Gather facts so the questions are about decisions, not things you could look up:

- The ticket, if there is one: summary, description, every AC, comments. Fetch it once through the project's scripts where they exist, and its parent. The agreed version goes into the handoff file, and later stages work from that, re-fetching only to check for changes.
- Parent epic, blockers and linked tickets. Fetch a blocker when it changes what "done" means, e.g. a table or schedule the ticket reads. Check whether the blocker's code is merged, in an open PR, or nowhere.
- The code the ticket touches, and existing config flags, read from the commit (`git show HEAD:<file>`) when the developer keeps local overrides in the working tree.
- The developer's memory (if they have any) and the repo's `AGENTS.md` / `CLAUDE.md` for standing rules.
- Work in flight around the ticket: list open PRs and in-progress tickets that touch the same files (`gh pr list`, the sibling subtasks). If the remaining work mostly overlaps a teammate's, raise it before round 1, because picking a different ticket is cheaper than three-way conflicts. Before recommending a stack on another branch, list what this ticket needs from it (symbols, routes, data shapes) and check whether main already has each one. Stack only for what main lacks; a data shape can usually be seeded instead.

Finding _facts_ is your job, never the developer's. When a question needs a fact from the code, another repo or a tool, send a sub-agent with a fresh context window to find it, and ask it for a short answer: file:line and one line per finding. Don't ask the developer for anything you could look up yourself. Don't block on a lookup: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report. Ask the rest of the frontier now. The _decisions_ are the developer's: put each one to them and wait.

## Domain language

When the grill is about a project's design, load the `domain-modeling` skill before round 1 and read the repo's glossary and ADRs (the skill says where they live). Word questions in the glossary's terms. When the developer uses a term that clashes with the glossary, or a vague word, raise it in the round. Update the glossary as each term is settled, and offer an ADR only on the skill's three tests.

## Knowledge check

Load the `knowledge-map` skill and run its `status` with the paths the work touches. For each area it says to explain first, round 1 opens with that area's explain-back question, asked before you give the answer, and the rest of the grill explains in that area's user terms before its code terms.

## Direction

If the project has a direction note (a step addition names it), read it before round 1. When the ticket touches something on its list (a shared data shape, a second way of doing something), put that choice to the developer as one question, with the cheapest option that keeps the direction open as your recommendation. Ask only where the choice would be hard to change later. Anything that only matters later is a "for later" note, not scope.

## Rounds

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the developer's answers before the next round.

Format a round like this:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

For example:

```
❓ **Q1** - **Blocker**: Ticket 98's schedule code is only on its PR branch. Stack on that branch and
seed schedules directly in dev, rather than wait for it to merge?

➡️ Recommend: stack on it, because this ticket needs its code; switch the base to main once it
merges. (If the other branch only touches the same files, ask whether to branch from main instead.)
```

Word each question so "yes" accepts your recommended answer.

Word each question in terms of what the user or agent does and sees, then give the code detail. "Should an agent be able to reschedule a call the customer answered?" comes before "make `callAnswered` a literal". Questions asked in code terms come back as "what do you mean?".

Keep each recommendation to one choice. If an answer doesn't map to exactly one option (a "yes" to a recommendation with parts, or a rule stated without its scope), restate it in the user's terms and confirm before asking the next round. A recommendation with parts gets misread or answered ambiguously.

Each round the developer answers reshapes the tree: settled decisions push the frontier outwards and unblock the questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Expect the developer to change the ticket as you go ("ignore the blocker, we'll seed the data", "use the most frequent, not the first"). Log each change as ticket drift, because the ticket wording will need updating later.

## Questions that usually matter

- **ACs that conflict** with what the developer says, or with existing patterns. Note every change: the ticket will need rewording.
- **Where each AC comes from:** for a subtask, trace each AC back to its parent story or the epic. An AC with no source is a question for the developer, not a rule. Quote the source line when you cite it. Examples in an epic often turn into rules in a subtask.
- **Data the ticket prescribes:** a new field, status, index or table named in the ticket or epic. Check whether an existing one already holds the fact, and recommend reusing it. Epics planned outside the code have specified parallel status fields and indexes nothing read.
- **Ordering rules** for multiples (first, most frequent, latest?) and tie-breaks.
- **Real values:** when the change compares, parses or formats data (names, SKUs, doses, dates), look at real dev values before asking and use their awkward cases (decimals, shared prefixes, empty values) in the questions and the tests. Dev data shows formats, not which states real flows reach, because it is seeded to exercise statuses; ask the developer, or trace the code that writes it.
- **Time**: UTC vs UK time, "N weeks after" what timestamp, clock changes.
- **Failure behaviour**: must the main flow carry on if this part fails?
- **Retries**: can this step run twice (Step Functions retries, re-sent events)? What stops duplicates?

## Done

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Summarise the understanding and get it confirmed. Don't act on it until the developer confirms you have reached a shared understanding.
