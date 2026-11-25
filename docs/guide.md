# User guide

Jig is a set of Claude Code skills, scripts and agents for taking work from an idea to a merged change on any project. A pack adds one organisation's rules on top. Each repository keeps a small settings file that tells the core how that repository works.

## Aims

1. **Code as documentation.** Answers come from names, types, tests and scripts, not from documents and comments that drift. A document is written only for what nothing executable can hold.
2. **Determinism.** A script answers a lookup the same way every time, and a check or hook enforces a rule. The agent is told less and proves more: every claim about code or a live system cites the script output or file line it came from.
3. **The AI does no more work than it needs to.** Scripts do the mechanical steps (fetching a ticket, rendering a transcript, writing the ledger), so the agent spends its tokens only on work that needs judgement. Workers and graders run on cheaper models.
4. **Improvement over time.** Every run ends with a retro and a grade. Each lesson becomes a script, a lint rule, a hook or a step addition before anyone considers a written rule. Good grades earn the agent more autonomy; bad ones take it away.

## Credits

This workflow stands on other people's work. Each borrowed skill keeps its licence and, where it was taken straight from upstream, an `upstream/` folder with that version, so changes from upstream are easy to carry in.

- **Matt Pocock**, [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). The thinking half of the workflow is his: the grill (`grilling`, `grill-me`, `grill-with-docs`), `domain-modeling`, `codebase-design` and `improve-codebase-architecture`, the `to-spec` and `to-tickets` steps, `implement`, `implement-spec` and `review-change`, and `tdd`, `diagnosing-bugs`, `prototype`, `triage`, `handoff`, `writing-for-agents`, `research` and `teach`. `setup-workflow` grew out of his `setup-matt-pocock-skills`. His licence is in [LICENSE-mattpocock-skills](../LICENSE-mattpocock-skills).
- **Lauren Tan**, [pstack](https://github.com/cursor/plugins/tree/main/pstack) in cursor/plugins (MIT). The doing half follows her approach: scripts drive the mechanical steps so the agent only does what needs judgement. Two of her principles are the core's own ("build the lever" and "encode lessons in structure"), and the verification skill and the worker status (`PASS`, `ISSUES` or `BLOCKED`) come from pstack.
- **Jesse Vincent and Prime Radiant**, [Superpowers](https://github.com/obra/superpowers) (MIT). Superpowers gave the idea of building a workflow of my own as a set of skills. Nothing specific is taken from it.

The retro, the grader and the autonomy ladder are this workflow's own.

## The loop

| Step | Skill | What happens |
|---|---|---|
| 1. Grill | `grill-with-docs` | Claude interviews you in rounds until the design is settled, and writes the glossary and ADRs as terms and decisions settle. |
| 2. Spec and tickets | `to-spec`, `to-tickets` | The spec, then tickets with blocking links, sizes and the areas each is likely to touch. |
| 3. Implement | `implement-spec` or `implement`, then `review-change` | Implementers build the tickets and run the checks, then three fresh reviewers (Standards, Spec and Correctness) review the whole change. `drive.py` owns the order of the run. |
| 4. Retro | `retro`, `grade-run` | Grade the run, count repeated lookups, and turn each lesson into something executable. |

Steps 3 and 4 run spec to PR: implementer subagents work the tickets in their own worktrees, a merger joins their work on an integration branch, then the whole change is reviewed and each ticket is graded. A pack can add an interactive mode, where you approve each checkpoint of one ticket, and share the same review, grader, ledger and retro.

## Install

You need macOS, Linux or WSL on Windows, with Claude Code, git and Python 3. Native Windows is not supported: the scripts need bash, real symlinks and `python3`. With WSL, run Claude Code inside WSL too, so `~/.claude` is the Linux one. The GitHub CLI (`gh`) is needed only if your tickets are GitHub issues.

```bash
git clone https://github.com/arpydev/jig.git
cd jig
./install.sh --dry-run
./install.sh
```

A pack is optional. To add one, run both commands with `--pack <pack folder>`.

`install.sh` links the core's skills, agents and hooks, and each pack's, into `~/.claude`. It registers the hooks listed in each `hooks/hooks.json` in `settings.json` (the core's are `context-guard`, `zsh-guard`, `git-guard`, `outbound-guard`, `docs-guard` and a skills-check reminder on every prompt), adds an import of `preferences.md` to `~/.claude/CLAUDE.md`, and asks once whether you own the core. Answer yes only if you maintain your own copy of Jig: the retro then proposes edits to it, rather than drafting an issue for its maintainer. It is safe to rerun. Anything already in the way is reported as a conflict and left alone. With `--backup`, it is moved to `~/.claude/skills-backup/` and the link is made; nothing is deleted. A skill that both the core and a pack have is linked from the core.

Start a new Claude Code session afterwards so the skills load.

To remove Jig, run `./uninstall.sh --dry-run`, then `./uninstall.sh`. It removes the links that point into the core or an installed pack, the hook entries `hooks.py` recorded, the `preferences.md` import and the `workflow-*` record files. It keeps `skills-backup/` and `agents-backup/`, and never touches a repository's settings, verification skill or run data.

## Set up a repository

Run `/setup-workflow` in the repository. Its scripts find what they can (the tracker, the check command, the glossary), and it asks you only the rest. It writes `.claude/workflow.json`:

```json
{
  "version": 1,
  "committed": true,
  "tracker": { "kind": "github" },
  "checks": "pnpm check",
  "docs": { "glossary": "GLOSSARY.md", "adr": "docs/adr" },
  "runData": ".claude/workflow-runs",
  "verifySkill": "verify-myapp",
  "steps": { "retro": ["docs/agents/grading.md"] }
}
```

- In a team repository that hasn't adopted the workflow, set `committed` to `false`. The settings and the verification skill are then hidden with `.git/info/exclude`, and the core never stages them.
- `runData` holds the friction logs, handoffs, grades and ledger. Run data always stays in the project, never in the core.
- `verifySkill` is the project's verification skill: how to check that each feature works, with a feature map. Setup writes a skeleton; each run that touches a feature fills in its entry.
- Check the file at any time with `python3 ~/.claude/skills/setup-workflow/scripts/settings.py check`.

The full format is in [settings.md](../skills/setup-workflow/references/settings.md).

### Step additions

A step addition adds a file or a skill to one step of the loop, such as the questions that matter in your project's grill. Each core skill loads its own step's additions when it reaches that step, with `settings.py steps <step>`. This is how a pack or a project adds its rules without changing the core.

```json
"steps": {
  "grill": ["~/packs/acme/steps/grill.md"],
  "design": ["~/packs/acme/steps/design.md"],
  "tickets": ["skill:acme-ticket-writing"]
}
```

The steps are `grill`, `domain`, `design`, `spec`, `tickets`, `plan`, `build`, `deploy`, `verify`, `review` and `retro`.

## The core skills today

| Skill | Use it to |
|---|---|
| `setup-workflow` | Write a repository's settings and verification skill skeleton. Also writes the `docs/agents/*.md` files Matt Pocock's engineering skills read. |
| `grilling` | Be interviewed in rounds until nothing is silently assumed. Claude looks facts up itself and asks you only for decisions, each with a recommended answer. |
| `grill-me` | Start a grill. |
| `grill-with-docs` | Start a grill that also keeps the glossary and ADRs up to date. |
| `domain-modeling` | Challenge terms against the glossary, settle vague words, check claims against the code, and write ADRs only for decisions that are hard to reverse, surprising and a real trade-off. |
| `codebase-design` | Use one vocabulary for design (module, interface, depth, seam, adapter, leverage, locality), keep code and infrastructure simple to change, and let the code explain itself. |
| `improve-codebase-architecture` | Scan a repository or an area for deepening opportunities, see them as an HTML report, and grill through the one you pick. |
| `comment-report` | Sort every comment in a repository or folder into Tautology, Excuse, Stale or Decision Record, and report what should replace each. It never edits. Based on a prompt Matt Pocock posted. |
| `implement` | Build one piece of work from a spec or tickets. |
| `implement-spec` | Build a whole spec: implementer subagents work its tickets in parallel worktrees, driven by `drive.py`, and a merger joins them on an integration branch. |
| `review-change` | Review the changes since a ref along three axes (Standards, Spec and Correctness) in parallel fresh subagents. |
| `retro` | Keep a friction log during a run, then grade it, count the lookups and propose the few changes that would have prevented the costliest friction. |
| `grade-run` | Grade a run with a fresh grader and record it in the ledger. |
| `to-spec` | Turn the grilled conversation into a spec: each decision with its why and the alternative weighed, what was checked and needs nothing, and the test data needed. |
| `to-tickets` | Split a spec, plan or epic into tickets that can run in parallel, with blocking edges, a test per acceptance criterion and the folders each is likely to touch. |
| `teach` | Learn a topic, a codebase or Jig itself over several sessions. Claude keeps what you know in `~/.claude/teach/<topic>/`, out of every repository, and teaches Jig from its own docs. |
| `tdd`, `diagnosing-bugs`, `prototype`, `triage`, `handoff`, `writing-for-agents`, `research` | Matt Pocock's skills, as he wrote them apart from a few renames. |

## Grading and autonomy

A separate agent with no context grades each run from primary sources only: the transcript, the ticket, the diff and the reviewer's raw report. It never sees Claude's summary of how the run went.

- Five gates set the grade to F or cap it at D: a false claim, an unapproved outward action, personal data, an unmet acceptance criterion, or a high-severity defect at merge.
- Seven criteria are scored 0 to 4: correctness, evidence per acceptance criterion, triage or test first, avoidable corrections or loop-backs, scope and standards, honesty of the friction log or report, and long-term effect.
- `scripts/ledger.py add` copies the grader's scores into the ledger word for word. Claude never changes a score.
- You grade blind first, and escaped defects found later lower old grades. These two are what keep the grader honest.

The ledger starts at autonomy level 0, where every checkpoint waits for you. Level 1 lets the scripts build, check and merge without stopping; the grill, the plan and the PR still wait. Level 2 lets spec to PR run unattended until an irreversible or outward action. The bar for each level is at the top of the ledger. You decide every change of level, and any gate hit or escaped high-severity defect drops a level at once.

## Packs

A pack is a folder with `skills/`, `agents/`, `hooks/`, step addition files and a `pack.json`. It holds one organisation's facts and rules, which the core never does. Skills the pack lists in `projectSkills` load only in the repositories that use them, so a company's release skills don't appear in a personal project.

A typical pack adds its tracker settings, its own grill, domain and design rules as step additions, and skills for its releases, ticket writing and code conventions.
