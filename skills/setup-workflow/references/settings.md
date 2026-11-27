# Project settings

Each repository has one `.claude/workflow.json` in its main checkout. Core skills read it with `scripts/settings.py`, never by reading the file. Run `settings.py check` after any change.

```json
{
  "version": 1,
  "committed": true,
  "tracker": { "kind": "github", "tickets": "gh issue view <n> --json number,title,body; blockers from \"Blocked by #n\" lines" },
  "checks": "pnpm check",
  "implementers": 3,
  "worktreeSetup": "pnpm install --frozen-lockfile && cp \"$MAIN/.env.local\" .",
  "ratchet": "scripts/ratchet.py",
  "docs": { "glossary": "GLOSSARY.md", "adr": "docs/adr" },
  "runData": ".claude/workflow-runs",
  "verifySkill": "verify-myapp",
  "models": { "correctnessReviewer": "sonnet" },
  "steps": { "grill": ["docs/agents/grill-questions.md"] }
}
```

| Key | What it holds |
|---|---|
| `committed` | `false` in a team repository: `settings.py exclude` hides this file and the verify skill with `.git/info/exclude`, and the core never stages them. |
| `tracker` | Where issues live for `to-tickets` and `implement-spec`: `github`; `gitlab`; `local` with `dir`; `jira` with `site` and `keyPattern` (such as `ABC-[0-9]+`); or `other` for any tracker described in `docs/agents/issue-tracker.md`. `tickets` says how to fetch a spec's tickets with their blockers: a command or an instruction, agreed at setup for the tracker in use. `implement-spec` needs it. |
| `checks` | The one command that runs the project's checks. |
| `implementers` | Optional, default 1. How many implementer subagents `drive.py` lets run at once. |
| `worktreeSetup` | Optional. The command `drive.py` runs in each new worktree; `$MAIN` is the main checkout. |
| `workerAgent` | Optional, default `worker`. The agent a skill starts for one narrow, well-briefed task. `check` fails when no agent of that name is installed. |
| `ratchet` | Optional. Where the repository's copy of `ratchet.py` is. `check` fails when it differs from the core's copy. |
| `docs` | Where the glossary and ADRs are. A path outside the repository keeps them out of git. |
| `runData` | Where friction logs, handoffs, grades and the ledger go. |
| `verifySkill` | The project's verification skill. |
| `models` | Optional overrides of the core's model per role: `session`, `sonnet`, `opus` or `haiku`. The roles and their defaults are in `ROLES` in `settings.py`; skills read them with `settings.py model <role>`. |
| `projectSkills` | Optional. Pack skills this repository uses, as paths to their folders. `settings.py link` links them into `.claude/skills`. A pack names them in its `pack.json`, and `install.sh` doesn't install them for every repository. |
| `ast` | Optional. The AST tool chosen for each language, such as `{"typescript": "node_modules/typescript"}`. The `ast` skill saves it with `settings.py set ast.<language> <tool>`. |
| `steps` | Optional step additions, below. |

## Step additions

A step addition adds content to one step of the loop, such as a pack's grilling questions. Each generic skill loads its step's additions when it reaches that step: it runs `settings.py steps <step>`, reads each file it prints and loads each `skill:<name>`.

| Step | Loaded by | Example |
|---|---|---|
| `grill` | `grilling` | questions that matter in this project |
| `domain` | `domain-modeling` | where company facts live, writing rules |
| `design` | `codebase-design`, `improve-codebase-architecture` | the repo's own patterns, its packages |
| `build` | `implement-spec`, `implement` | the files implementers read, how to trim the checks' output |
| `verify` | `implement-spec`, `implement` | how to run the end-to-end tests, for one ticket and for the whole suite |
| `review` | `review-change` (the Standards reviewer) | conventions skills, extra review checks |
| `spec` | `to-spec` | what this project's specs must cover |
| `tickets` | `to-tickets` | ticket-writing skill, sizes, tracker steps |
| `plan`, `deploy` | not loaded by a core skill yet | deploy steps |
| `retro` | `grade-run`, `retro` | the project's standards for the grader |

Each addition is a file path (absolute, `~/`, or relative to the repository) or `skill:<name>` to load a skill. To add one, put it in the list for its step and run `settings.py check`, which fails if the file or skill is missing.

```json
"steps": {
  "grill": ["~/my-pack/steps/grill-shop.md"],
  "design": ["~/my-pack/steps/design-shop.md"],
  "deploy": ["~/my-pack/steps/deploy-shop.md"],
  "tickets": ["skill:shop-ticket-writing"],
  "review": ["skill:api-conventions", "skill:ui-conventions"]
}
```
