---
name: improve-codebase-architecture
description: Scan a repo (or an area of it) for deepening opportunities in code and infrastructure, present them as a visual HTML report, then grill through whichever one the developer picks. Runs only when the developer types /improve-codebase-architecture, optionally followed by an area to focus on.
disable-model-invocation: true
---

<!-- Local fork of mattpocock/skills improve-codebase-architecture (MIT, see ../../LICENSE-mattpocock-skills). The upstream/ folder holds the version this fork was taken from. Every local change is listed under "Local changes" at the end. -->

# Improve Codebase Architecture

Find architectural friction and propose **deepening opportunities**: refactors that turn shallow modules into deep ones, and infrastructure that can be made simpler. The aim is code that is easy to test, easy to change and easy for an agent to find its way around.

This is the whole-repo or named-area version. The retro's architecture check is the small version that only looks at one run's diff.

This command uses the project's domain model and a shared design vocabulary:

- Load the `codebase-design` skill for the architecture vocabulary (**module**, **interface**, **depth**, **seam**, **adapter**, **leverage**, **locality**) and its principles (the deletion test, "the interface is the test surface", "one adapter = hypothetical seam, two = real"). Use these terms exactly in every suggestion. Don't drift into "component", "service", "API" or "boundary". The exception is when you name a real layer of the repo's documented pattern, because that is the class's name.
- Apply its **"The repo's own patterns win"** and **"Simple and easy to change"** sections. Look for depth inside that layout.
- The repo's glossary and ADRs (see `domain-modeling` for where they live). The glossary gives names to good seams. ADRs record decisions this command should not reopen.
- This step's additions: run `python3 ~/.claude/skills/setup-workflow/scripts/settings.py steps design`, read each file it prints and load each `skill:<name>`. They name the repo's packages, pattern docs and direction note, and win over this skill where they disagree.

## Process

### 1. Explore

**Scope before you scan: YAGNI.** Deepening a module pays off by making future changes to it easier, so give extra weight to the parts of the codebase that have changed recently. Decide *where* to look before you look:

- If the developer named a direction (a module, a package, a pain point, an epic's area), take it and skip the inference below.
- Otherwise, run `git fetch` and walk back a good stretch of `origin/main` history (`git log --oneline -100 origin/main`, then `--stat` on the busy ones) to find the hot spots: the files and areas that keep coming up. Read `origin/main`, not the working tree or the current branch, because local checkouts go out of date. If the changes are scattered with no clear hot spot, widen the net.
- If the repo has separate packages, name which ones are in scope.

Before exploring, read:

- the glossary and any ADRs in the area you're looking at;
- the repo's direction note, if it has one, so candidates that make the direction easier rank higher, and none build ahead of it;
- the repo's pattern docs and `CLAUDE.md`. Where those docs and the code disagree, the code is the source of truth.

Then start a fresh `general-purpose` agent to walk the scoped area. Tell it that it is read-only, give it the paths and docs above, tell it to load `codebase-design`, and ask it to report candidates in that skill's vocabulary. Don't give it rigid heuristics. Let it explore and note where it meets friction:

- Where does understanding one concept mean bouncing between many small modules?
- Where are modules **shallow**, with an interface nearly as complex as the implementation?
- Where have pure functions been pulled out just for testing, while the real bugs hide in how they're called (no **locality**)?
- Where do tightly coupled modules leak across their seams?
- Where is the same rule written in more than one service, handler or frontend page?
- Which parts are untested, or hard to test through their current interface?
- Infrastructure: two fields or statuses for one fact, and tables, indexes, queues, Lambdas, env vars or IAM grants that nothing reads.

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, it concentrates" is the signal you want.

Then check each candidate's files against open PRs (`gh pr list --state open` and the files they touch). Mark a candidate that overlaps a teammate's open PR, so the developer can pick work that doesn't collide.

### 2. Present candidates as an HTML report

Write a self-contained HTML file outside the repo: the session's scratchpad directory if there is one, otherwise `$TMPDIR` (falling back to `/tmp`). Name it `architecture-review-<repo>-<timestamp>.html` so each run gets a fresh file. Show it to the developer (`SendUserFile` with `display: "render"` in the desktop app, otherwise `open <path>`) and give the full absolute path.

The report is **fully self-contained: inline CSS, hand-built HTML and inline SVG diagrams, no scripts and no CDN links**. The app's file panel doesn't run scripts, so a Tailwind or Mermaid CDN leaves the report unstyled. Use call-flow columns for graph-shaped relationships and more editorial visuals (mass diagrams, cross-sections) where they fit. Each candidate gets a **before/after visualisation**. Be visual.

For each candidate, render a card with:

- **Files**: which files and modules are involved (including CDK constructs and stacks for infrastructure)
- **Problem**: why the current architecture causes friction
- **Solution**: a plain-English description of what would change
- **Benefits**: in terms of locality and leverage, and how tests would improve
- **Before / After diagram**: side by side, illustrating the shallowness and the deepening
- **Recommendation strength**: `Strong`, `Worth exploring` or `Speculative`, shown as a badge
- **Open PR overlap**, if any: one line naming the PR

End the report with a **Top recommendation** section: which candidate you'd tackle first and why.

**Use the glossary's vocabulary for the domain, and `codebase-design`'s vocabulary for the architecture.** If the glossary defines "Check-in", talk about "the check-in scheduling module", not "the CheckInHandler", and not "the check-in service".

**ADR conflicts**: if a candidate contradicts an existing ADR, only raise it when the friction is real enough to reopen the ADR. Mark it clearly in the card (for example, an amber callout: _"contradicts ADR-0003, but worth reopening because…"_). Don't list every theoretical refactor an ADR rules out.

See [HTML-REPORT.md](HTML-REPORT.md) for the HTML scaffold, diagram patterns and styling guidance.

Do NOT propose interfaces yet. After the file is written, ask the developer: "Which of these would you like to explore?"

### 3. Grilling loop

Once the developer picks a candidate, load the `grilling` skill and grill them to walk the decision tree: constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive, and what other repos would feel the change. Before trusting a claim about another repo, `git fetch` it and read its `origin/main`.

Side effects happen inline as decisions settle. Load the `domain-modeling` skill to keep the domain model current as you go:

- **Naming a deepened module after a concept not in the glossary?** Add the term, and say which term you added.
- **Sharpening a vague term during the conversation?** Update the glossary there and then.
- **Developer rejects the candidate with a lasting reason?** Offer an ADR: _"Want me to record this as an ADR so future architecture reviews don't suggest it again?"_ Only offer when a future reviewer would need the reason to avoid suggesting the same thing. Skip short-lived reasons ("not worth it right now") and obvious ones. Ask before writing each ADR.
- **Want to explore alternative interfaces for the deepened module?** Use `codebase-design`'s [DESIGN-IT-TWICE.md](../codebase-design/DESIGN-IT-TWICE.md) parallel sub-agent pattern.

### 4. Turn the outcome into work

When the grill reaches a shared understanding, ask the developer what to do with it. Don't start refactoring.

- **A tech-debt ticket** (the usual outcome): first search the tracker for an open ticket on the same area and offer to add to it instead. Otherwise draft one, with the ticket-writing skill the `tickets` step additions name if there is one. Show the draft, and create it only after the developer approves. No size estimate.
- **Small enough to do now:** say so, and leave the choice of whether and where to do it to the developer.
- **Not now:** nothing to write, unless an ADR was agreed above.

## Local changes

Taken 2026-11-23 from github.com/mattpocock/skills at commit abeeaf9 (`skills/engineering/improve-codebase-architecture/`, MIT licence). `upstream/grilling.md` is `skills/productivity/grilling/` from the same commit; the core `grilling` skill carries it now. `upstream/agents/openai.yaml` is upstream's Codex metadata. Claude Code doesn't use it; it's kept so the upstream diff stays complete. When upstream changes, diff it against `upstream/`, carry the changes in, keep the changes below, then replace `upstream/`.

| Date | Change | Why | Upstream? |
|---|---|---|---|
| 2026-11-23 | Glossary and ADRs come from where `domain-modeling` says, not `GLOSSARY.md` and `docs/adr/` in the repo | Team repositories keep them out of git | Local only |
| 2026-11-23 | Read the direction note, the repo pattern docs and `CLAUDE.md` first; the repo's agreed ports are never a candidate; layer names are allowed as names | The repo's patterns win over `codebase-design`, as in that fork | Local only |
| 2026-11-23 | Infrastructure is in scope (duplicate state, unread tables, indexes, grants) | Matches `codebase-design`'s "Simple and easy to change" section | Propose upstream |
| 2026-11-23 | Hot spots from `origin/main` after `git fetch`; name the packages in scope | Local checkouts go out of date | Local only |
| 2026-11-23 | Mark candidates that overlap a teammate's open PR | The developer picks work that doesn't collide with teammates' | Propose upstream |
| 2026-11-23 | Report goes to the session scratchpad and is shown with `SendUserFile` | Desktop app shows it inline | Local only |
| 2026-11-23 | No Tailwind or Mermaid CDN: inline CSS and hand-built diagrams, no scripts | The app's file panel doesn't run scripts; the first report came out unstyled with raw Mermaid text | Local only |
| 2026-11-23 | Cross-repo impact in the grill; the grill uses the core `grilling` skill (it was bundled as `GRILLING.md` until 2026-11-24) | Changes can reach sibling repos | Local only |
| 2026-11-23 | New step 4: outcome becomes a tech-debt ticket, created only after approval | Matches the retro architecture check and the confirm-before-writing rule | Local only |
| 2026-11-24 | Project paths, packages, writing rules and the ticket-writing outcome moved to a pack's `design` step addition | The core holds no company facts | Local only |
