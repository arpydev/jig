# Run 1-8: review triage

The orchestrator checked each finding in `1-8-review.md` against the code. Item numbers are the review's. "C" is Correctness, "S" is Standards and "P" is Spec.

## Confirmed, to fix (review-fix agent)

| # | Fix |
|---|---|
| C1 | `skills/implement-spec/SKILL.md` step 8 copies `<runData>/runs/<spec>*` into the PR. That now includes `-plan.json`, `-proof.json` and `-pr.md`, which #5 says never go in the repository. Exclude them in step 8. If drive.py has a helper that lists the files to copy, exclude them there too. |
| C2 | `skill_overlap.py:29` uses `abspath`, so running it through the install symlink `~/.claude/skills/writing-for-agents` gives `~/.claude` as the core. Use `realpath`. Add a test that runs it through a symlinked skill folder without `--core`. |
| C3 | `typescript.mjs` loads a saved relative `ast.typescript` path, such as `node_modules/typescript`, relative to the working directory and as a bare `require` specifier, so it crashes. Resolve the saved value against the repository root. Add a test that loads from a saved relative setting. |
| C4 | `release.sh` pushes the tag, then `release`. A rejected `release` push leaves the tag on origin and no GitHub release. **Developer's decision:** push both with `git push --atomic`. Extend `test_never_overwrites_a_release_branch_that_moved_elsewhere` to assert that no new tag reached origin. |
| C5 | In call-tree `extract.mjs`, `calleeOf` takes `declarations[0]`. For an overloaded function that is a signature with no body, so the function and everything it calls are dropped. Use the declaration with a body, or the resolved signature's declaration. Add a test with an overloaded function. |
| C6 | In status-flow `extract.mjs`, every from-state in a function pairs with every to-state. A guard clause (`if (s === "Cancelled") throw/return; s = "Shipped"`) draws `Cancelled -> Shipped`. Sibling branches (`if (s==="Draft") s="Review"; else if (s==="Review") s="Published"`) draw `Draft -> Published`. Pair each comparison in an `if` condition with the assignments in its own then-branch. A guard whose branch only exits pairs with nothing after it. Keep today's behaviour for the plain cases the existing tests cover, and add a test for each of the two examples. |
| C7 | `track_record.py` `gh()` calls `sys.exit` on any error, so one bad repository (409, 404, SSO 403) stops the whole build. Skip that repository, name it in the output, and carry on. Add a test. |
| C8 | `work_repos` doesn't deduplicate by slug, so a second clone or a worktree folder counts every PR twice. Deduplicate by slug. Add a test. |
| C9 | The `ORIGIN` regex only matches `github.com`, so an SSH host alias such as `git@github-work:org/repo.git` is silently dropped. Accept any host with an `owner/repo` path. Non-GitHub hosts then fail in gh and are skipped and named by the C7 fix. The `slug in projects` check in `reviews_given` is case-sensitive. Compare case-insensitively. Add tests. |
| C10 | **Developer's decision (changes #1's order):** in `ast_tool.py find`, a saved `ast.<language>` setting wins over a single local tool, and the local tool is used only when nothing is saved. Update the ast SKILL.md wording and the tests. |
| C11 | `ast_tool.py chosen()` treats any `settings.py get` failure, including invalid JSON, as "nothing saved". Only a missing key means nothing saved. Surface any other error. Add a test. |
| C12 | `drive.py diagram` doesn't check `--ticket` against the run's tickets. Refuse an unknown ticket. Add a test. |
| C14 | `drive.py:467`: the "no proof yet" message leaves out the fix hint that the mismatch message gives. Add it. |
| C15 | `settings.py set` doesn't validate. Run `problems()` on the result before writing and refuse if there are any, so the file is unchanged. Add a test, for example that `set ast foo` is refused. |
| C16 (part) | `merged_prs` stops at `--limit 1000` without saying so. Warn when the limit is hit. |
| C17 | **Developer's decision:** the snapshot keeps repo names by default, with an optional alias map (a JSON file next to the snapshot in `~/.claude/report/`, mapping `owner/repo` to a neutral name) applied to project names in the snapshot. Add one line in the track-record SKILL.md. Add a test that a mapped repo name is absent from `snapshot.json`. |
| S2 | `ast_tool.py` copies `main_checkout()` (and `fail`) from `setup-workflow/scripts/settings.py`. Reuse the original the way `track_record.py`'s `sibling()` loads another skill's module, or call `settings.py`, rather than duplicating it. |

## Rejected, with reasons (shown to the developer)

- **C5, same-name node ids:** ids are `<file>#<name>` by design, so a plan diagram written before the code matches the proof. Adding line numbers would break that match. This is a known limit, not a bug.
- **C13, proof compares files, not code:** this is inherent to the #5 design (ADR "Diagrams prove the work and then go"). Reported, not fixed.
- **C16, rework uses committedDate / bot reviews / calibration rows:** these are measurement choices, not bugs. They go in the report for a later look.
- **S4, long docstrings:** the ratchet passes (`ratchet.py check`: ok). Docstrings aren't `#` comments.
- **S, parseArgs duplicated in two kinds:** there are only two callers, and the kinds are meant to stand alone. Borderline. Revisit at a third kind.
- **S, track_record.py size and dict-passing, vague `cell` and `tag` names:** judgement calls with no failure. Left as they are.
- **S, kinds/\*/package.json without a `why:`:** JSON has no comments, and the file only sets ESM for the folder.
- **S, groups.ts:** asked for by #7, and the developer confirmed the groups.
- **P, plugin-only pairs dropped:** neither skill can be changed, so the pair can't be acted on. Mixed pairs are labelled, which meets the intent.
- **P, settings.py `set`, missing proof blocks, `diagram plan` clears the old proof, merge.mjs, .gitignore node_modules:** each is needed for its ticket's behaviour. `set` saves #1's choice. A missing proof is the "no proof" case of #5's gate. Clearing stops a stale proof from matching. merge.mjs closes #2's open item, as #5 asked. node_modules is needed for the #8 website build in a worktree.
- **P, #3 TS 7 check lives in typescript.mjs, not ast_tool.py:** the kinds are the TypeScript users, and they ask for a 5.x path as #3 says.
- **C, #3 can't be compared with the old extractor:** the developer agreed #3 builds the kind from scratch (see Agreed in `drive.py status`).

## Open, not code

- #6 real-install output on the PR, and #8's one-off `release` push: outward actions that wait for the developer's yes.
