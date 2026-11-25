# Glossary

Words for the workflow the core implements.

**Core**
The generic workflow skills, hooks, agents and scripts that work on any project. Installed once in `~/.claude/skills`. Holds no company facts. Its repository is called Jig.
_Avoid_: base skills, generic skills

**Pack**
A skill pack: one person's or one organisation's own skills, step files and hooks, kept in their own folder and added on top of the core. Custom skills always go in a pack. A pack skill can later move into the core.
_Avoid_: extension, profile, plugin

**Grill**
An interview in rounds, run by the `grilling` skill, until nothing about a design or plan is silently assumed. Claude looks facts up itself and asks the developer only for decisions, each with a recommended answer. The first step of the loop.
_Avoid_: interview, Q&A

**Project settings**
The files that tell the core how one repository works: its tracker, checks, deploy and dev-test steps, where run data goes, and whether its glossary and ADRs are kept in the repository.
_Avoid_: profile, config

**Driver**
The scripts that own the order of a run's mechanical steps (branches, worktrees, checks, merges) and say when an agent is needed. Agents do only the work that needs judgement.
_Avoid_: orchestrator

**Autonomy level**
How many checkpoints a project's runs may pass without waiting for the developer, from 0 (every checkpoint waits) upwards. Recorded in each project's ledger and earned through graded runs.
_Avoid_: trust level, mode

**Verification skill**
A project's own `verify-<project>` skill: how to check that each feature works, with a feature map. Read instead of exploring the code again.
_Avoid_: test skill, dev-testing

**Feature map**
The part of a verification skill that lists, for each feature, where its code, routes and tests are and how to check it.
_Avoid_: index, code map

**Worker status**
The last word of every implementer's and worker's report: `PASS`, `ISSUES` or `BLOCKED`.
_Avoid_: result, outcome

**Step addition**
A pointer in the project settings that adds pack or project content to one step of the loop, such as the grilling questions or one project's deploy steps.
_Avoid_: extension, hook (a hook is a Claude Code hook), override

**Decision log**
The run's record of each decision made without asking the developer, one line each with what was decided and why. Kept at every autonomy level.
_Avoid_: audit log, friction log (the friction log records what slowed a run down)

**Teaching workspace**
One topic's folder in `~/.claude/teach/<topic>/`, where the `teach` skill keeps what the developer is learning: the mission, learning records, lessons and notes on how they like to be taught. Never inside a repository.
_Avoid_: knowledge bank, learner profile
