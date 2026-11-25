---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

<!-- From mattpocock/skills implement-spec by way of another project (MIT, see ../../LICENSE-mattpocock-skills). It arrived already changed, so there is no upstream/ snapshot. That project's own rules moved to its build and verify step additions. -->

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec.

The issue tracker should have been provided to you: `settings.py get tracker.tickets` says how to fetch the spec's tickets and their blockers. If it prints nothing, stop and tell the user to run `/setup-workflow`.

The goal is the entire spec implemented on a single **integration branch**, with every ticket resolved the way the issue tracker closes work.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

**The driver.** `python3 ~/.claude/skills/implement-spec/scripts/drive.py` (called `drive.py` below) owns the order of the run's mechanical steps: the task graph, worktrees, the record of agents, report results, the checks, merges, gates, the decision log and the list of steps. You start the agents and make the judgement calls; the driver does everything else, and says when an agent is needed. Do what it prints. Its state lives in `<runData>/runs/<spec>-state.json`, so `drive.py status <spec>` tells any session where the run stands.

Start every subagent with a fresh context window.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.

Settings come from `python3 ~/.claude/skills/setup-workflow/scripts/settings.py` (called `settings.py` below). Before starting, run `settings.py steps build` and `settings.py steps verify`, read each file they print and load each `skill:<name>`. They are this project's rules for building in worktrees and for running its end-to-end tests, such as the files implementers read, and they win over this skill where they disagree. Pass each implementer the paths of the files, not their contents.

**Implementer subagents** should be run in the background where possible, as many at once as `drive.py next` lists (the `implementers` setting).

**Models.** Each role's model comes from `settings.py model <role>` (`implementer`, `explorer`, `merger`); when it prints `session`, leave the model unset. Implementers use the default model by default, because their grades decide autonomy; revisit once the ledger has a few graded specs. The exploration subagent and merger subagents run on Sonnet by default: their work is searching and merging, not design.

Every ticket is graded afterwards by the `grade-run` skill, and its ledger sets the **autonomy level** that decides which merges need the developer. Read the current level before starting: `python3 ~/.claude/skills/grade-run/scripts/ledger.py level`. Grading files for this spec go in `<runData>/runs/` (`settings.py get runData`), named `<spec>-...` where `<spec>` is the spec issue number. A run of loose issues with no spec issue is named `<first>-<last>` (for example `13-20`).

**Decisions and steps.** Anything you decide without asking the developer goes in the decision log: `drive.py decide <spec> "<what>" --why "<why>"`. Mark each step with `drive.py done <spec> <step>` when it is finished. A step you leave out is `drive.py skip <spec> <step> --reason "<why>"`, never dropped silently: the grader reads the reason. The steps are `explore`, `tickets`, `review`, `e2e`, `grade`, `pr`, `cleanup` and `retro`. What the next session needs and the state can't show goes in a note, which `drive.py status` prints: `drive.py note <spec> pr|agreed|open|ships "<text>"` for the draft PR, anything the developer agreed that differs from a ticket, items left for the orchestrator, and actions due when it ships (such as a production migration).

**Two stages.** Stage A is steps 1 to 6, until every ticket is merged or blocked. Stage B, steps 7 to 10, runs in a fresh session so the review and grading don't share stage A's long context. `drive.py next` prints the brief for stage B when stage A is over.

## Steps

1. Read the spec and tickets to understand the task graph. Fetch the tickets as `tracker.tickets` says and write them once to `<runData>/runs/<spec>-tickets.json`: a JSON list of `{"id", "title", "blockedBy": [ids], "touches": [paths]}`, where `touches` is the folders in backticks in the ticket's "Likely to touch" list (`to-tickets` names each area's folder). Where a ticket names areas without folders, map each area, or the files an issue names, to the repository's folders and log the mapping with `drive.py decide`. A ticket with none gets `[]` and runs alone. Run `drive.py tickets --check <file>` until it prints `ok`, and act on its warnings. For loose issues with no spec issue, write the tickets file by hand from the issues, and tell the grader there is no parent spec.

2. (optional) Use an **exploration subagent** only when the tickets need library docs or code outside the areas they name. Skip it when the tickets build on code earlier milestones' implementers already worked in. Ensure the exploration subagent can save files - it should save its markdown notes in a directory outside the repo, accessible by all future subagents. The notes summarise with `file:line` pointers and links; they don't paste whole files or doc pages, which every implementer would then read again. This lets **implementer subagents** focus on implementation rather than exploration. Run it after step 3, record it with `drive.py started <spec> --work explore --agent <id>`, and mark the `explore` step done or skipped with its reason.

3. Create the integration branch: `drive.py start <spec> --tickets <file> --base <branch>`, where the base is the branch the spec builds on. It creates `claude/<spec>` and its worktree. If the issue tracker closes work through PRs, or the user asks for one, open a draft PR after the first merge in step 5 (a branch with no commits ahead of main can't open one; `drive.py merge` reminds you), marked as closing the spec and tickets, and record it with `drive.py note <spec> pr <link>`.

4. Run `drive.py next <spec>`. For each ticket it says to start, run `drive.py worktree <spec> <ticket>`: it cuts the ticket's own branch and worktree from the integration tip and runs the project's `worktreeSetup`. Then use a fresh **implementer subagent** for the ticket in that worktree. The Agent tool starts it in the main checkout, so its prompt opens with the worktree's absolute path and tells it to work only there. Record it as you start it with `drive.py started <spec> <ticket> --agent <id>`; the grader finds the transcript by that ID. Each implementer subagent:
   - reads only its ticket, the parts of the spec the ticket points to, the project's coding standards, its glossary (`settings.py get docs.glossary`), its architecture notes, any ADR the ticket names, the exploration notes and the build and verify additions, not the project's whole read-first list (the roadmap and full design spec are for planning sessions). Say so in its prompt;
   - checks `git -C <worktree> branch --show-current` names its ticket branch before starting, and stops with `BLOCKED` if not;
   - calls the Skill tool with `tdd` to build the ticket, and follows [references/tests.md](references/tests.md): every new test must catch something real, shown by a break table in its report;
   - merges the integration branch tip into its own branch and runs the project's checks with `drive.py checks <spec> <ticket>` (it saves the full output and prints the tail) before reporting done;
   - when the ticket touches what the end-to-end tests cover, runs only the end-to-end tests it added or changed, plus any covering what it changed, as the verify additions say, and puts their passing output in its report; "written but not run" is not done. It never runs the whole suite: that runs once in step 7;
   - stays inside its branch: it never pushes, merges into main, opens a PR, runs `drive.py merge`, or edits or closes an issue;
   - ends with a report listing each acceptance criterion with the test or command output that proves it, and anything unmet, skipped, worked around or still open. The report is graded against the transcript, so it says plainly what did not work. Its last line is `PASS`, `ISSUES` or `BLOCKED`.

5. Once an **implementer subagent** completes, save its report word for word as `<runData>/runs/<spec>-<ticket>-report.md` and run `drive.py report <spec> <ticket> <that file>`. Do what it prints:
   - `PASS`: merge it with `drive.py merge <spec> <ticket>` as soon as that ticket is approved. Don't hold several tickets back to merge together: each one merged sooner gives the next implementers a newer base and leaves the merger fewer conflicts. The driver squash-merges the ticket into the integration branch as one commit, runs the checks there, and undoes the merge if they fail. At autonomy level 0 it stops (exit 3) and names what to show the developer: the ticket, the implementer's report as given and the diff summary. Merge only on their approval, with `--approved`; a declined ticket goes back to a fresh implementer with their reason, logged with `drive.py decide`. At level 1 the driver merges without asking and logs it. Keep every ticket branch until it is graded.
   - Items the report says only the orchestrator can close (a CI result on the PR, the PR description) are not issues: record each with `drive.py note <spec> open` and close it in stage B.
   - `ISSUES`, or checks that failed after a merge: start a fresh fix agent (an implementer subagent with the same rules) in the ticket's worktree, pointing it at the report or the checks log. Record it with `started`, and report again when it finishes. The driver allows two fixes, then marks the ticket blocked.
   - `BLOCKED`, or a report whose last line is none of the three: the driver drops the ticket and every ticket behind it. Tell the developer which and why, and carry on with the rest.
   - A merge conflict (exit 2): start a **merger subagent**, one ticket per merger, in the ticket's worktree. It merges the integration branch into the ticket branch, resolves the conflict keeping what both sides meant, runs `drive.py checks <spec> <ticket>` and commits. Record it with `started`, then run `drive.py merge` again.

6. If this changes the **frontier** of available tickets, run `drive.py next <spec>` and kick off more **implementer subagents** for the new tickets. This allows for maximum concurrency, except between tickets whose "Likely to touch" areas overlap: the driver starts those one after the other, the second from the integration branch after the first is merged. Parallel tickets on the same area cost a long merge and can drop each other's work. Repeat steps 4 to 6 until `drive.py next` says stage A is over, then run `drive.py done <spec> tickets`, give the developer the stage B brief it printed, and stop.

7. Stage B starts with `drive.py status <spec>`. Once all tickets are complete, call the Skill tool with `review-change` on the integration branch, against the branch it started from, with the spec and the run `<spec>`. It saves its raw report as `<runData>/runs/<spec>-review.md` before anything is fixed; the grader reads the raw report. Triage it as `review-change` says, then fix all confirmed issues in a single fresh **implementer subagent**, recorded with `drive.py started <spec> --work review-fix --agent <id>`. Then run the full end-to-end suite once on the integration branch, as the verify additions say, and save the result summary in `<runData>/runs/<spec>-e2e.md`. A failure here goes back to the review-fix implementer, then the full suite runs again. Mark `review` and `e2e` done.

7b. Grade every ticket: call the Skill tool with `grade-run` and follow it, one grader per ticket, starting the graders together. Record each with `--run "#<ticket> of #<spec>"`. Report the grades and any blind grades due to the developer before step 8. Mark `grade` done.

8. If runData is inside the repository, copy the run's records (`<runData>/runs/<spec>*`, except the state and the checks logs) into the integration worktree and commit them there, so they go with the PR. Run `drive.py gate <spec> pr-ready --what "mark the PR ready"`; on `wait`, ask the developer first. If a draft PR exists, mark it ready for review. Otherwise, report the integration branch, and resolve each ticket the way the issue tracker closes work once the developer agrees: closing an issue is an outward action, which always waits. Mark `pr` done.

9. Clean up all **implementer subagent** worktrees with `drive.py cleanup <spec>`. It refuses until the `grade` step is done or skipped, and keeps the branches.

10. End with the retro: call the Skill tool with `retro` for the run `<spec>`. The tickets are already graded (7b), so it skips its grading step. Mark `retro` done.
