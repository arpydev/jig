---
name: setup-workflow
description: Set a repository up for the core workflow skills. Writes its project settings (.claude/workflow.json) and the skeleton of its verification skill. Use once per repository before the other core skills, or when the developer asks to change a project's settings.
disable-model-invocation: true
---

# Set up a repository

Scripts prove what they can. Ask the developer only what they can't.

1. Run `scripts/detect.py --repo <repo>`. If `settingsExists` is true, run `scripts/settings.py check` and change only what the developer asks.
2. Draft the settings from the facts, in the format in [references/settings.md](references/settings.md):
   - `tracker`: `github` when `githubRepo` is set; otherwise ask.
   - `worktreeSetup`: what a fresh worktree needs before it builds (installing packages, copying ignored files such as `.env.local` from `$MAIN`, the main checkout), starting from the `packageManager` `detect.py` reports; leave it out when nothing is needed.
   - `checks`: the `check` package script if there is one, run with the package manager; otherwise ask.
   - `docs`: the found glossary and ADR folder; otherwise `GLOSSARY.md` and `docs/adr`.
   - `verifySkill`: the found `verify-*` skill; otherwise `verify-<repository name>`.
3. Ask in one message, each with a recommendation:
   - Is this a team repository? Team means `committed: false`, and the glossary and ADRs go outside the repository.
   - Where should run data go? Recommend `.claude/workflow-runs`.
   - Which pack project skills does this repository use (`packProjectSkills`)? Recommend those already in `linkedSkills`.
   - Which tracker does this project use? Recommend GitHub. Then agree `tracker.tickets`: how `implement-spec` fetches a spec's tickets with their blockers, as a command or an instruction. For GitHub, recommend `gh` with the repository's native issue dependencies. Jira or any other tracker (kind `other`) gets its own setup: work out with the developer how its tickets and blockers are read, and record that.
   - How many implementer subagents may run at once (`implementers`)? Recommend 1 until a spec has run, then what the machine's test suites allow side by side.
   - Is the drafted `worktreeSetup` right, and does a worktree need any ignored file copied from `$MAIN`?
   - Any step additions from a pack?
4. Show the JSON, then write it to the path `settings.py path` prints. Run `settings.py check` until it prints `ok`. Run `settings.py link` for the project skills. When `committed` is false, run `settings.py exclude`.
5. If the verify skill doesn't exist, run `scripts/verify_skeleton.py <verifySkill> --repo <repo>`.
5b. Offer the lint rule ratchet: `scripts/ratchet.py install <repo> [--to scripts/ratchet.py]` copies it in (standard library only). If the developer wants it, set `ratchet` to the copy's path, add `python3 <copy> check` to the project's checks, and rerun `settings.py check`. Then offer the starter rule, which stops new comments: `python3 <copy> add comments --command "python3 <copy> comments" --reason "Let names, types and tests carry the meaning; mark a reason the code can't show with why:"`. Today's comments become the baseline, and the `comment-report` skill finds which to remove. Other rules are added later with `ratchet.py add`, usually from a retro.
6. If the repository uses Matt Pocock's engineering skills (`to-spec`, `to-tickets`, `triage`) or the core's `implement-spec` and `review-change`, they read `docs/agents/*.md`. Write those with [references/agents-docs.md](references/agents-docs.md), taking the glossary and ADR paths from the settings.
7. Report what was written. Don't commit anything.
