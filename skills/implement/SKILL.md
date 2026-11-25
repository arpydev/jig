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

Run typechecking regularly, single test files regularly, and the full test suite once at the end. The project's checks are `settings.py get checks`.

Once done, call the Skill tool with "review-change" to review the work.

Commit your work to the current branch.
