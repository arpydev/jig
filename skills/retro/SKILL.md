---
name: retro
description: The retro step shared by every workflow skill (implement-spec, implement, and a pack's delivery or release skills). Keep a friction log while a workflow skill runs, then at the end grade the run, count the lookups and propose the few changes that would have prevented the costliest friction, and apply only the ones the developer approves. Use when a workflow skill reaches its retro step, or when the developer says "let's do a retro on the skill", "what slowed us down", or "improve the skill from this run".
---

# Retro

Every run of a workflow skill should leave it a little better. That only works if the evidence is written down while it happens and the changes are chosen carefully afterwards. A skill that grows a rule for every one-off gets slower and noisier, not better.

Run data lives in the project, never in the core: `<runData>` below is `python3 ~/.claude/skills/setup-workflow/scripts/settings.py get runData`. Run `settings.py steps retro` and read each file it prints before you start: it names the project's standards, its shared skills and anything else the project adds to this step.

Only change the developer's own workflow skills. Shared skills (a team's conventions skills, plugin skills) aren't ours to change. Name the gap for the developer instead of editing or drafting them.

## During the run: keep a friction log

At the start of the run, create `<runData>/runs/<run>.md` (create the folder if it isn't there) using the template below. `<run>` is what the skill names it: the ticket key, the spec, the release version or the epic key. At the same time, if a session-renaming tool is available (`set_session_title` with `session_id: "self"` in the desktop app), rename the session to `<run>: <short summary>`; skip this if there isn't one. It matters because the developer finds past runs in the sidebar by that key and the app's own title often leaves it out. Add a line as soon as one of these happens, while the details are fresh:

- **Correction**: the developer corrected something you got wrong. Pushback that turns into a discussion (weighing scope, now or a follow-up, how much a point matters) is part of the work, not friction, so don't log it.
- **Wrong assumption**: something you stated or relied on turned out false.
- **Loop back**: you had to redo a step or go back a phase.
- **Stall**: something blocked progress, such as an expired login, a missing permission, a hook that blocked a call, a shell error or a tool that fought back.
- **Missed by the checklist**: something the skill's steps should have caught but didn't.
- **Added by the developer**: something the developer asked for that the skill didn't cover.

One line each: the step, what happened and what it cost. No personal data, no credentials and nothing the project's rules keep out of files.

If the run is short and nothing went wrong, say so at the end and skip the retro.

## At the end: grade, check the architecture, then the retro

Before the retro itself, for runs that changed code:

1. **Grade the run** with the `grade-run` skill. A fresh agent grades Claude from the transcript, ticket, diff and raw review, and the result goes into `<runData>/grades.md` unchanged. Ask for the developer's blind grade before showing the grader's. Start by checking the last five graded runs for escaped defects. The autonomy ladder is the one `ledger.py` writes into the ledger; `ledger.py level` prints the current level.
2. **Run the architecture check** with `references/architecture-check.md`, but only when the diff changes a module's shape (that file says when). A fresh agent looks for deepening opportunities in the code the run touched.

When both run, start them together, since neither needs the other's result. Their findings join the retro candidates below. The grader's "what would most have improved this run" line is a candidate like any friction entry.

For every run that explored, whether or not it changed code, **count the lookups** with `references/lookups.md`. `scripts/lookups.py` lists the run's exploration calls from its transcripts. Group them by the question they answered and add them to the shared `<runData>/lookups.md` tally. A question that passes the threshold there becomes a retro candidate whose fix is a script. This can run alongside the grader.

## Every fifth retro: step back

Alongside the pruning pass, look across runs rather than at this one: `<runData>/grades.md` (which criteria keep scoring low, especially C7), the "Worth exploring" architecture notes (an area that keeps coming up), `<runData>/learnings/`, `<runData>/lookups.md` (questions close to the threshold, and scripts no run used, per `references/lookups.md`), and the tech-debt issues raised. Propose at most one longer-term item: a tech-debt issue or epic, an ADR, or a change to how the workflow works. The developer decides whether it goes ahead.

Then look for a skill overlap: run the `writing-for-agents` skill's `scripts/skill_overlap.py` (`python3 -I ~/.claude/skills/writing-for-agents/scripts/skill_overlap.py`). Read its pairs, and its rows for skills nothing loads and nobody used, and propose at most one merge or removal, approved like any other retro change. Plugin skills are read-only. When the developer approves merging skill B into skill A:

1. Copy both skills' folders to `$TMPDIR` before editing anything.
2. Fold what B does that A doesn't into A, then delete B's folder and, in the core, its entry in `website/src/lib/groups.ts`.
3. Write a config with `"old"` set to the two copies and `"new"` to A's folder, run `python3 <core>/scripts/no_regression.py <config>` (`<core>` is the repository two folders up from the real path of `~/.claude/skills/retro`), and show the developer every line of B and of the old A that didn't survive, so each loss is chosen rather than missed.
4. Keep B as an alias skill (it only loads A, and only the developer can start it) only if the developer says they still type `/B`.

An approved removal deletes the skill's folder and its group entry the same way.

## The retro

Read the friction log and the session, then present candidates to the developer, most costly first. For each one give:

1. **What happened**: one or two lines from the log.
2. **Root cause**: why the skill let it happen.
3. **Where the fix belongs**. Work down this list and pick the first that fits. Anything code or a live system can prove belongs in the environment, not in a written rule or memory: a rule can be skimmed and a memory goes stale, but a script or check gets it right every time. Build the lever: do a step by hand the first time, then script it, and make the script safe to rerun. Encode lessons in structure, not in prose.
   - **A script**: the answer can be worked out from code or live systems, so a script works it out on demand and returns a small result. It goes in the skill's `scripts/` folder, follows the rules in `references/lookups.md`, and gets a line in its repository's Scripts index.
   - **An automated check or hook**: a mechanical mistake a lint rule, test, CI job or hook could catch. A lint rule goes in through the ratchet: `python3 ~/.claude/skills/setup-workflow/scripts/ratchet.py add <rule> --command '<command>' --reason '<why>'` in the project, so the breaches that already exist become its baseline and the count can only go down.
   - **This skill**: the workflow was missing a step, check or warning.
   - **The repo's `AGENTS.md` or shared skills**: a rule every agent in that repo should follow. Name the gap; don't edit or draft it.
   - **Memory**: only what the environment can't prove, such as the developer's preferences, team agreements, and decisions with their reasons.
   - **Nothing**: a one-off. Say so; not everything needs a rule.
4. **The proposed change**: the exact wording or diff.

Three good changes beat ten weak ones. Word each change as a general principle with its reason, not a rule tied to one ticket's classes, files or messages.

If the developer has already asked you to fix the friction, that approves fixing it. Still show what you changed.

## Changes to the core

A fix that would help any project (a core skill, script, hook or `preferences.md`) goes to the core, not to a pack or the project. Read `~/.claude/workflow-core.json`; a missing file means `owner` is false.

- **Owner** (`"owner": true`): propose the edit to the core like any other change, and make it in the core's repository once approved.
- **Not owner**: draft an issue for the core's repository: what happened, the root cause and the proposed change, with no project data in it. Show the draft; post it only after the developer approves the wording.

## Applying changes

- Apply only the changes the developer approves.
- Before adding a rule, check `<runData>/learnings/<skill>.md` and `<runData>/applied/<skill>.md`. If the same thing happened before, the case for a change is strong. If it's the first time and minor, log it in `learnings/<skill>.md` as seen once and act if it recurs.
- Prefer sharpening an existing line to adding a new one. Explain the reason in the wording, so a later run can judge edge cases.
- Propose removals as well as additions: a rule written in more than one place, a rule a newer line now covers or makes wrong, a rule that hasn't mattered in several runs, and prose that a script, check or hook now enforces. Keep `SKILL.md` lean and put detail in the reference file for the step it affects. A long checklist gets skimmed, and skimming is how things get missed.
- Every fifth retro of a skill (count the run logs in `<runData>/runs/` whose `Skill:` line names it), or when its `SKILL.md` passes 150 lines, start the retro with a pruning pass over the whole skill, not just this run's lessons: merge rules said in more than one file, cut ones a newer line covers, and drop ticket-key anecdotes while keeping their reason. Show the cuts for approval like any other change. Per-run retros only ever add, so without this the skill only grows.
- Record each lesson in `<runData>/learnings/<skill>.md`: one row per lesson, with the runs it came from and what was done. Once a lesson is in a script, check, the skill or memory, move its row to `<runData>/applied/<skill>.md`, so `learnings/` holds only lessons still waiting to recur.
- If a lesson applies to several workflow skills, fix it in each one or here, and say which.

## Templates

`<runData>/runs/<run>.md`:

```markdown
# <run>: <summary>

Started: <date>  Repo: <repo>
Sessions: <session id>
Skill: <the workflow skill running>

## Friction log
| Step | Type | What happened | Cost |
|---|---|---|---|

## Retro outcome
| Lesson | Fix went to | Change |
|---|---|---|
```

`<runData>/learnings/<skill>.md` and `<runData>/applied/<skill>.md`, if they aren't there yet:

```markdown
# Learnings across runs: <skill>

Read this before each run. Bump a lesson's count when it recurs. Lessons now in the skill or memory are in `applied/<skill>.md`.

| Lesson | Seen in | Count | Status |
|---|---|---|---|
```
