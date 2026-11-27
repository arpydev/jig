---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

<!-- From mattpocock/skills by way of another project (MIT, see ../../LICENSE-mattpocock-skills). It arrived already changed, so there is no upstream/ snapshot. -->

Implement the work described by the user in the spec or tickets.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Before starting, run `python3 ~/.claude/skills/setup-workflow/scripts/settings.py steps build` and `settings.py steps verify`, read each file they print and load each `skill:<name>`. They are this project's rules for building and testing, and they win over this skill where they disagree.

Call the Skill tool with "tdd" where possible, at pre-agreed seams.

When a `diagram` kind covers the change, draw the plan diagram with the plan: extract the current graph, write the graph you expect after the change, run `python3 ~/.claude/skills/implement-spec/scripts/drive.py diagram <ticket> plan <current.json> <expected.json>`, and show the drawing with the plan. Whether that waits for the developer follows the autonomy level, like the rest of the plan. Once the tests pass, extract the real graph and run `drive.py diagram <ticket> proof <current.json> <actual.json> --kind <kind>`. A mismatch is a failing test at every autonomy level: fix the code, or agree a new plan diagram with the developer. All graph files go in `<runData>/runs/` (`settings.py get runData`), never in the repository. A PR body takes the `<ticket>-pr.md` it writes. When no kind covers the change, follow `diagram`'s stop-and-ask.

Run typechecking regularly, single test files regularly, and the full test suite once at the end. The project's checks are `settings.py get checks`.

Once done, call the Skill tool with "review-change" to review the work.

Commit your work to the current branch.
