# Decisions

The choices that shape Jig, each with the reason it was made. Terms are defined in the [glossary](../GLOSSARY.md).

## Shape

### The core holds no organisation's facts

The core is generic. Anything specific to one person or organisation (its tracker, its release steps, its ticket style, its own skills) goes in a pack, which sits on top of the core. A check in the pack fails if any of its facts reach the core.

**Why:** the core can then be shared and reused as it is, and a pack can change without touching anyone else's workflow.

### Packs add to steps rather than wrapping skills

A project's settings list step additions: files or skills that a core skill loads when it reaches that step, such as a pack's grill questions or one project's deploy steps.

**Why:** a pack or project adds its rules without copying or wrapping a core skill, so a core update reaches everyone and nothing exists twice.

### One installed copy, settings per project

The core is installed once into `~/.claude`. Each repository keeps only its settings in `.claude/workflow.json`. In a team repository that hasn't adopted the workflow, the settings are hidden with `.git/info/exclude` and never committed.

**Why:** one copy to update, and one person can use the workflow in a team repository without changing it for the team.

### Familiar skill names

Skills use Matt Pocock's names where he has one for the step (`grill-with-docs`, `to-spec`, `to-tickets`, `implement-spec`), and new names otherwise. The review is `review-change` because Claude Code ships its own `code-review`. Every skill forked from his names his licence and keeps his version in `upstream/`; the three that came in already changed by another project (`implement`, `implement-spec`, `review-change`) say they have no snapshot instead. A test enforces both.

**Why:** people who know his skills know these, and upstream changes are easy to diff and carry in.

## Scripts over prose

### Scripts drive the mechanical steps

In spec to PR, `drive.py` owns the order of the run: the ticket graph, worktrees, checks, merges, gates and records. The agent starts subagents and makes the judgement calls, and does what the driver prints. The run's state is one file, so any session can pick it up.

**Why:** a script does the same steps the same way every time, costs no tokens, and can't skip a step it was told about.

### Every lesson becomes something executable

When a run shows a mistake, the retro first looks for a script, a test, a lint rule, a hook or a step addition that would have prevented it. A written rule is the last resort.

**Why:** a script or check stays correct, while prose and memory go stale without anyone noticing and cost context on every load.

### A ratchet for any lint rule

A rule is any command that prints one breach per line. The ratchet keeps a per-file baseline, fails when a count goes up, and never lets the baseline rise.

**Why:** the retro can add a rule to existing code without fixing every old breach first, and the count can only fall.

### References are checked

A test fails when a skill names a script, reference file, step file or skill that doesn't exist.

**Why:** a broken path in a skill fails silently at run time; a test catches it before then.

## Spec to PR

### The spec and tickets are the plan

There is no separate plan file. The spec holds each decision with its why and the alternative weighed; each ticket holds its why, a test per acceptance criterion and the folders it is likely to touch.

**Why:** a second plan would repeat what the spec and tickets already say, and drift from them.

### The ticket graph is checked before any agent starts

The tickets are written once as a graph (id, blockers, likely folders) and validated: unique ids, known blockers, no cycles. Tickets whose folders overlap run one after the other.

**Why:** a bad graph fails cheaply, before any agent has spent tokens on it.

### Every worker ends with PASS, ISSUES or BLOCKED

On `ISSUES`, a fix agent runs and the checks rerun, at most twice. On `BLOCKED`, or a report with no valid status, that ticket and every ticket behind it stop; the rest carry on.

**Why:** the driver reads the result without an agent interpreting it, bounded retries keep cost down, and one stuck ticket doesn't stop the run.

### One squash merge per ticket

The driver squash-merges each ticket onto the integration branch, runs the checks there and undoes the merge if they fail. A merger agent runs only on a conflict.

**Why:** one commit per ticket keeps the branch readable, and most merges need no agent.

### Three fresh reviewers

`review-change` starts three reviewers in parallel, each with a fresh context: Standards, Spec and Correctness. Their raw reports are saved word for word for the grader.

**Why:** a reviewer that didn't write the code doesn't share its blind spots, and the grader reads what the reviewers said rather than a summary.

## Trust

### A fresh grader reads only primary sources

A grader with no context grades each run from the transcript, the ticket, the diff and the reviewers' raw reports. It never sees the agent's own account of how the run went, and its scores are copied into the ledger word for word.

**Why:** an agent grading its own summary grades the story, not the work.

### Autonomy is earned, one ladder for every mode

Every project starts at level 0, where every checkpoint waits. Good grades earn level 1 (build, checks and merges run without stopping) and level 2 (spec to PR runs until an irreversible or outward action). The grill, the plan and outward actions always wait. The ladder is a table in `ledger.py`, which answers each gate and writes the ledger's text.

**Why:** autonomy follows evidence, and one table means the rules and the code can't disagree.

### Unasked decisions are logged

At every level, each decision made without asking adds a line to the run's decision log, and a skipped step stays on the step list with its reason.

**Why:** unattended work stays reviewable, and the grader can tell a chosen skip from a forgotten one.

### Diagrams prove the work and then go

When a diagram kind covers a change, Claude draws a plan diagram before building and checks a proof diagram read from the code once it works. A mismatch stops that agent at every autonomy level, like a failing test, until the code is fixed or the developer agrees a new plan diagram. The graph files live in the run's data folder, never in the repository; only the result line and the merged diagram reach the PR.

**Why:** a mechanical check that the work matches the agreed plan earns trust in unattended runs with several agents, and diagrams kept in the repository would go stale.

### Outward actions always wait

Posting a comment, creating an issue or opening a pull request needs the developer's yes, at every level. Hooks ask for it too.

**Why:** these are hard to take back and speak for the developer.

## Projects

### A verification skill per project

Setup writes each project a `verify-<project>` skill with a feature map. A feature's entry is filled in the first time a run touches it, and the retro keeps it current.

**Why:** runs stop exploring the same code again, and checking a change works becomes a known list of steps.

### The cheapest model that does the job

The grill and planning use the session's model. Workers, mergers and the grader use a cheaper one, and only judgement-heavy review uses the strongest. A project can override each role that `settings.py model` lists; the grader always runs on Sonnet.

**Why:** most of a run is mechanical or narrow, and tokens spent there buy nothing.
