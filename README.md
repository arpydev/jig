# Jig

A generic Claude Code workflow core: skills, agents, scripts and hooks that take work from an idea to a merged change on any project. It holds no organisation's facts. Your own skills and rules go in a skill pack (see **Pack** in [GLOSSARY.md](GLOSSARY.md)).

Start with the [user guide](docs/guide.md), or read it alongside every skill on the website: [jig-neon.vercel.app](https://jig-neon.vercel.app/).

## Principles

- **Build the lever.** Do a step by hand the first time, then script it. Scripts are safe to rerun.
- **Encode lessons in structure.** A repeated instruction becomes a script, check or hook. Prose and memory keep only what nothing executable can prove.

## Install

You need macOS, Linux or WSL on Windows, with Claude Code, git and Python 3. Native Windows is not supported.

```bash
git clone https://github.com/arpydev/jig.git
cd jig
./install.sh --dry-run
./install.sh
```

Add `--pack <folder>` to both commands to install a skill pack as well. `install.sh` links the skills, agents and hooks into `~/.claude`, registers the hooks in `settings.json`, adds an import of `preferences.md` to `~/.claude/CLAUDE.md`, and is safe to rerun. Start a new Claude Code session afterwards, then run `/setup-workflow` in each repository.

To update, run `./update.sh --dry-run`, then `./update.sh`. It moves the core to the latest release tag, pulls each installed pack that has a remote, removes links to skills a release dropped, and reruns `install.sh`. A session-start hook says when a newer release is out, checking at most once a day. Owners of the core pull main instead and get no prompt.

To remove it, run `./uninstall.sh --dry-run`, then `./uninstall.sh`. It removes only what `install.sh` added: links into the core or an installed pack, the hook entries it recorded, the `preferences.md` import and its record files. Backups and each repository's own files stay.

## Scripts

Each script answers one question on demand, so skills don't keep the answer in prose. The opening comment of each script gives its usage.

| Script | Question it answers |
|---|---|
| `install.sh` | Are the core's and each pack's skills, agents and hooks linked into `~/.claude`? |
| `update.sh` | Is the core on the latest release, with every installed pack pulled and relinked? |
| `release.sh` | What is the next release version, and what goes in its notes? |
| `uninstall.sh` | What did `install.sh` add to `~/.claude`, and can it be removed? |
| `scripts/hooks.py` | Are the hook entries from each `hooks/hooks.json` in `settings.json`? |
| `scripts/skill_refs.py` | Does every skill name only scripts, files and skills that exist? |
| `scripts/no_regression.py` | Did moving skills between the core and a pack lose any line? |
| `skills/setup-workflow/scripts/detect.py` | What can be proven about this repository (remote, scripts, glossary, routes)? |
| `skills/setup-workflow/scripts/settings.py` | What do this repository's workflow settings say, and are they valid? |
| `skills/setup-workflow/scripts/ratchet.py` | Has any lint rule's breach count gone up? |
| `skills/setup-workflow/scripts/verify_skeleton.py` | What should a new verify skill start from? |
| `skills/implement-spec/scripts/drive.py` | What is the next mechanical step of a spec-to-PR run? |
| `skills/grade-run/scripts/transcript.py` | What did a run do, as plain text for the grader? |
| `skills/grade-run/scripts/ledger.py` | What grades has the project recorded, and what is the autonomy level? |
| `skills/knowledge-map/scripts/knowledge.py` | How well does the developer know the area this work touches, and is their evidence still fresh? |
| `skills/retro/scripts/lookups.py` | Which lookups did a run repeat that a script could answer? |
| `skills/ast/scripts/ast_tool.py` | Which AST tool does this repository use for a language? |
| `skills/to-tickets/scripts/publish.py` | Are the approved ticket drafts on GitHub, with their blocked-by links? |

## Releasing

Users are prompted to update only when a new `vX.Y.Z` tag reaches GitHub, so a change on main reaches them only once it is released. When a skill or two is ready, run `./release.sh --dry-run`, then `./release.sh`. It works out the version from the commit titles since the last tag: a patch if every title starts with "Fix", otherwise a minor. A major happens only with `--major`. The notes are those titles. It asks before it tags, pushes and publishes the GitHub release.

## Tests

```bash
python3 -m unittest discover -s tests
```

## Website

`website/` is an Astro site built from this repository's own files: the guide, glossary, decisions and each skill. A skill missing from `website/src/lib/groups.ts` fails the build.

It needs Node 22.23.4 or newer (`website/.nvmrc` says 24).

```bash
cd website
nvm use
npm install
npm run dev
```

To host it on Vercel, set the project's root directory to `website`.

## Licence

Jig is MIT licensed: see [LICENSE](LICENSE). Many skills are forked from Matt Pocock's [mattpocock/skills](https://github.com/mattpocock/skills) and also carry his MIT notice in [LICENSE-mattpocock-skills](LICENSE-mattpocock-skills). The [user guide](docs/guide.md#credits) lists every credit.
