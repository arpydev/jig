---
name: review-change
description: "Review the changes since a fixed point (commit, branch, tag, or merge-base) along three axes: Standards (does the code follow this repo's documented coding standards?), Spec (does the code match what the originating issue/spec asked for?) and Correctness (would it break at runtime, and did any safeguard get weaker?). Runs the three reviews in parallel fresh sub-agents and reports them side by side. Use when a workflow skill reaches its review step, or when the developer wants to review a branch, a PR, work-in-progress changes, or asks to \"review since X\". Takes a ref, and optionally the spec."
---

<!-- From mattpocock/skills code-review by way of another project (MIT, see ../../LICENSE-mattpocock-skills), with a Correctness axis from the developer's own final review. It arrived already changed, so there is no upstream/ snapshot. -->

Three-axis review of the diff between `HEAD` and a fixed point the caller supplies:

- **Standards**: does the code conform to this repo's documented coding standards?
- **Spec**: does the code faithfully implement the originating issue / spec?
- **Correctness**: would the code break at runtime, and did any safeguard get weaker?

All three axes run as **parallel sub-agents** so they don't pollute each other's context, then this skill aggregates their findings. Start every sub-agent with a fresh context window. A reviewer who watched the build tends to confirm its decisions; a fresh one questions them.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-workflow`.

Settings come from `python3 ~/.claude/skills/setup-workflow/scripts/settings.py` (called `settings.py` below). Without project settings, `steps` prints nothing and `model` prints the core default, so this skill also works without them.

## Process

### 1. Pin the fixed point

Whatever the caller said is the fixed point (a commit SHA, branch name, tag, `main`, `HEAD~5`, etc.). If they didn't specify one, ask for it.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base). Also note the list of commits via `git log <fixed-point>..HEAD --oneline`. If the work has uncommitted changes, add `git diff HEAD` to what each sub-agent reads.

Before going further, confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail here, not inside three parallel sub-agents.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. A spec or ticket the caller passed as an argument.
2. Issue references in the commit messages (`#123`, `Closes #45`, GitLab `!67`, etc.), fetched via the workflow in the tracker doc.
3. A spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing is found, ask the user where the spec is. If they say there isn't one, the **Spec** sub-agent will skip and report "no spec available", and the **Correctness** sub-agent reviews the diff on its own.

### 3. Identify the standards sources

Search the repo for every file that documents how code should be written. When `CODING_STANDARDS.md` or `CONTRIBUTING.md` exists, it must be on the list. Then run `settings.py steps review --paths`: add each file it prints to the list. It prints each `skill:<name>` as that skill's `SKILL.md` path, because the worker agents have no Skill tool; the Standards sub-agent reads it like the other files. They are this project's review additions, and they win over the baseline below.

On top of whatever the repo documents, the Standards axis always carries the **smell baseline** below: a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation. Like any standard here, skip anything tooling already enforces.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name**: a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy**: a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change**: one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality**: abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest**: a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

The baseline also carries three checks for writing only what is useful. Like the smells, a documented repo standard overrides them:

- **Comment the code could carry**: a new or edited comment that repeats the code, excuses a hack, has gone stale, or explains what rather than why. → rename, extract a named function or constant, narrow a type, or write a test whose name states the rule; a reason the code can't show stays as one line starting `why:` (`codebase-design`, "Code that explains itself").
- **Tautological test**: an assertion that recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`), or a test that would still pass if the behaviour it names were broken. → take the expected value from an independent source: a known literal, a worked example, the spec (`tdd`, "Anti-patterns").
- **Nobody asked for it**: code, files, docs, config or tests the spec or ticket doesn't need, such as a helper for one caller, a README for a script, a test of a framework's own behaviour. → delete it.

### 4. Spawn the three sub-agents in parallel

Issue all three sub-agent calls together, in the foreground, and aggregate the reports they return. Use the agent `settings.py get workerAgent` names, or the core's `worker` when it isn't set. Each sub-agent's model comes from `settings.py model <role>`, with the roles `standardsReviewer`, `specReviewer` and `correctnessReviewer`; when it prints `session`, leave the model unset. The core defaults are Sonnet for Standards and Spec, to keep reviews within the plan's usage limits, and Opus for Correctness, which needs the judgement. If the Spec review starts missing behaviour the developer later catches, raise that before changing its model.

Give no sub-agent the plan, the conversation, your own findings or your view of the risky parts. Any of those anchors it. Every sub-agent is read only: no builds, deploys, pushes or writes of any kind. Tell each one to read whatever code its axis needs, beyond the files named, and to return its whole report in its reply, not as a file path: the worker agent's defaults say otherwise.

**Standards sub-agent prompt** should include:

- The full diff command and commit list.
- The list of standards-source files you found in step 3 (the skills' `SKILL.md` files among them), **plus the smell baseline from step 3** pasted in full (the sub-agent has no other access to it).
- The brief: "Report, per file/hunk where relevant, (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell or usefulness check you spot: name it and quote the hunk. Distinguish hard violations from judgement calls: documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** should include:

- The diff command and commit list.
- The path or fetched contents of the spec.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

**Correctness sub-agent prompt** should include:

- Where the change is: the diff command and commit list, or the PR link.
- Where the spec or ticket is, and its parent, so it reads them itself. Pointers only, not your summary.
- The checklist in [references/correctness.md](references/correctness.md), pasted in full.
- The brief: "Review the code for correctness bugs, gaps against the spec or ticket and its parent, weakened safeguards and missing tests. Give file, line and a concrete failure for each finding. Mark each finding **ours** (introduced by this diff) or **existing** (already there), and trace the code before claiming either."

If the spec is missing, skip the Spec sub-agent and note this in the final report.

### 5. Save and aggregate

When the caller names a run, save the three reports word for word as `<runData>/runs/<run>-review.md` (`runData` from `settings.py get runData`) before anyone triages them or fixes anything; the grader reads the raw reports.

Present the three reports under `## Standards`, `## Spec` and `## Correctness` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings, because the axes are deliberately separate (see _Why separate axes_).

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes: that's the reranking the separation exists to prevent.

### 6. Triage

The caller triages, not the reviewers. Check every finding against the code yourself, and confirm it or say why it's wrong. Show the developer the rejected ones too, with your reason, so they can overrule you. Existing problems are reported, not silently fixed.

## Why separate axes

A change can pass one axis and fail another:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**
- Code that does what was asked, in the house style, but loses a write when the second call fails → **Standards and Spec pass, Correctness fail.**

Reporting them separately stops one axis from masking another.
