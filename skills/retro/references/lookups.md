# Lookups: turning repeated exploration into scripts

If code or a live system can prove an answer, a script should work it out the same way each time. The agent shouldn't have to explore for it or remember it. Exploring costs tokens and wanders differently on each run. A script costs one call and returns only the small answer the step needs. This step finds the questions worth scripting by counting them across runs.

## After each run that explored

1. List the run's exploration. Pass the session files from the friction log's `Sessions:` line, oldest first:
   `python3 -I ~/.claude/skills/retro/scripts/lookups.py <file1> <file2> … > <scratchpad>/<run>-lookups.txt`
   The file gives the totals, the workflow scripts that ran, and one line per exploration call with its result size. A `---` line marks each developer message. Result contents are never printed.
2. Group the calls by the **question** they answered, not by tool. For example, "which PRs and repos belong to this ticket?", "what's on main since the last prod tag?", or "which handlers and stacks use this service?". Leave out calls that were part of the work itself, such as reading the file you were about to edit or checking your own change. Those can't be scripted.
3. For each question, check the Scripts index of the core's and each pack's README first. If a script already answers it, the run should have used that script. That's a friction entry: the skill step doesn't point at the script, or the script's output was missing something.
4. Update `<runData>/lookups.md` (shared by every workflow skill in the project). Add a run to a question's row when it comes up again, and add a row for a new question. Write questions in general terms, never with a ticket's data in them.

## When a question becomes a script

A question becomes a retro candidate, with "A script" as where the fix belongs, when either of these is true:

- it has come up in **3 runs**, in any skills
- it has come up in **2 runs** and costs more than about **10 calls or 20k characters** of results each time

A cheap question that comes up often (one grep) isn't worth a script to maintain. An expensive one probably is, even if it has come up only twice.

Every script must:

- **Print a short, structured result.** Write bulk output to files in `$TMPDIR` and print an index of them.
- **Say what it didn't find**, for example `linked PRs: none in <repo>`. If it silently leaves something out, the agent goes back to exploring and the script saves nothing.
- **Fail loudly** (a non-zero exit and a clear message) when a login, input or repo is missing.
- **Have a `test_<name>.py` next to it**, using unittest, runnable with `python3 -I`.
- **Return keys, IDs and statuses, never personal data**, and stay read-only unless writing is its stated job.
- **Get a line in its repository's README Scripts index** (name, the question it answers, inputs, output). The skill step that needs it names it directly.

When the script exists, set the question's status in `<runData>/lookups.md` to `Scripted: <name>`.

## Every fifth retro: unused scripts

Run `lookups.py --scripts-only` over the sessions of the last five runs. A script that ran in none of them is a candidate for removal. Either its step no longer needs it, or the step doesn't point at it. Show the candidate in the pruning pass like any other cut.
