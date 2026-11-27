# Run 1-8: review-change raw reports

`git diff main...HEAD` on claude/1-8 at 506c2c4. Spec: tickets #1 to #8, no parent spec. Saved before triage or fixes.

## Standards

**Hard violations (documented standards)**

1. **docs/decisions.md ADR vs skills/diagram/SKILL.md:** none found. The ADR "Diagrams prove the work and then go" matches the wiring in implement and implement-spec.

2. **codebase-design, "One place for each fact" / "Reuse before adding"** (skills/ast/scripts/ast_tool.py).
   `ast_tool.py` copies `main_checkout()` from `skills/setup-workflow/scripts/settings.py`. The body is identical apart from `fail`'s signature. `track_record.py` already shows the pattern to follow: its `sibling()` helper loads another skill's module. I rate this a hard breach because the standard is explicit about one place per fact. If you read it as a judgement call, it is still a clear Duplicated Code case.

3. **writing-for-agents, Local changes table:** the new row ("Runs scripts/skill_overlap.py before a new skill is created") records a local change. The one-line pointer sentence it adds also sits in the always-loaded part of SKILL.md. I'd treat that as acceptable, since it is a short context pointer with a trigger.

4. **Comment ratchet** (codebase-design, "Code that explains itself"): in the new scripts, no `#` or `//` comments lack a `why:` prefix. Docstrings are the only prose. Several are long and multi-line (`track_record.py` module docstring lines 2–14, `skill_overlap.py` lines 2–21, `ast_tool.py` lines 2–13). If the ratchet counts docstrings, they would need review. I haven't confirmed whether it does.

**Judgement calls (baseline smells, heuristics only)**

- **Duplicated Code:** `parseArgs` in `kinds/status-flow/scripts/extract.mjs` and `kinds/call-tree/scripts/extract.mjs`. Both build the same `flag(name)` splice closure, the same `args.length !== 1` check and the same `path.resolve(args[0])`. Extract a shared helper in `skills/diagram/scripts/`, next to `runKind` in `typescript.mjs`. With two kinds this is borderline, and it would grow with every new kind.
- **Duplicated Code:** `fail()` and `main_checkout()` are repeated across `ast_tool.py` and `settings.py` (see item 2).
- **Divergent Change, Primitive Obsession:** `track_record.py` is 532 lines. It mixes gh/git collection, signal calculation, the snapshot, and about 150 lines of embedded CSS and SVG rendering. Splitting out the rendering would make it easier to change. PRs and reviews are passed around as plain dicts and tuples.
- **Mysterious Name:** `sibling(skill, name)` (track_record.py:28) is acceptable, and its docstring helps. `cell()` (skill_overlap.py:209) and `tag()` (track_record.py:405) are vague. Names like `table_cell` and `snapshot_badge` would say more.
- **Speculative Generality (possible):** `kinds/*/package.json` hold only `name`, `private` and `type: module`. They exist to set ESM per folder. If that is intentional, it needs a `why:` line, and I didn't find one.
- **Nobody asked for it (possible):** `website/vercel.json` and the `release.sh` branch push belong to ticket #8, so they are in scope. However, `website/src/lib/groups.ts` adds the "diagram" and "ast" skills and a new "Your record" group. Check that this is requested.
- **Tautological tests:** none spotted in the `test_drive.py` DiagramTest hunks. They assert on independent literals such as `"changed edge Start -> Finish..."`. I did not read `test_track_record.py` or `test_status_flow.py` in depth.

No patient data or secrets seen.

ISSUES

## Spec

Spec review of main...HEAD against tickets #1 to #8. I read the diff and code only. I ran no tests, so nothing below is confirmed by a run.

**(a) Missing or partial**
- #6: "Plugin skills are labelled read-only in rows and pairs". Plugin rows are labelled. A pair of two plugin skills is dropped (`skill_overlap.py`: `if a["read_only"] and b["read_only"]: continue`), so it is never labelled. Mixed pairs are labelled. This is reasonable, but it is a deviation.
- #6: "Run against the real install, the report pairs `implement` with `implement-spec` and flags `grill-me` and `grill-with-docs`… output pasted on the PR". Nothing in the diff shows this was done. It is a manual criterion and still open.
- #8: "After the dashboard change, a push to main doesn't deploy…". This is manual by design. Also, the "create `release` at `v1.1.0`" one-off setup is not in the diff, and I did not check whether it was done.
- #3: "For a TypeScript 7 repository… the lookup asks for a TypeScript 5.x path". `ast_tool.py` knows nothing about versions. The check is in `typescript.mjs`, which exits 3 with a message to ask for 5.x. This works for the kinds, but the `ast` lookup itself doesn't do it. Check that the call-tree and status-flow tests cover a TS 7 fixture.

**(b) Scope creep**
- #1: `settings.py` gained a general `set <dotted.key> <value>` command. It is needed to save the choice, but it is a new public settings command the ticket didn't name.
- #5: `drive.py checks` and `drive.py merge` now fail while a plan diagram has no matching proof. #5 says "A mismatch stops the run at every autonomy level". A missing proof also blocks, which goes further than a mismatch.
- #5: `drive.py diagram plan` deletes the old proof and `pr.md`. Nothing asks for this.
- #5/#2: `merge.mjs` is a new script. #2 lists graph file, drawing, comparison and Mermaid, not a merge script.
- #8: `.gitignore` adds `node_modules/`. It is harmless, but no ticket asks for it.

**(c) Implemented but possibly wrong**
- #3 (agreed change): "nothing in the core points to it". `grep -rl status-flow` finds only the new kind, `tests/test_release.py` and `tests/test_status_flow.py`, so no skill points to the old folder. I did not open the two tests, so I can't say whether `test_release.py` is a stray hit.
- #3: the agreed change says no workplace-specific statuses or rules. `kinds/status-flow/references/rules-file.md` uses a generic ticket workflow (Open, Resolved, Closed), which looks acceptable. The rules file format is also new, so check it against "Pack rules files keep working unchanged". The agreed change builds the kind from scratch, so that is probably fine.
- #1: "returns the repository's own tool when there is one". `find` prints the single local tool even when settings name a different one, so the local tool always wins. That matches the ticket's order.
- #1: "replaces the `npm` mentions in `setup-workflow`'s settings reference with pnpm". The diff changes no existing line. `settings.md` already says pnpm on main, so there was nothing to replace.
- #6: the retro's step-back instructions look complete. They cover at most one merge or removal, deleting the folder and the group entry, `no_regression.py`, and the alias only on request. The retro text is only an instruction, and I did not check the "every-fifth" trigger wording.

PASS-level overall: no ticket looks wholly unimplemented. Nothing above is blocking.

ISSUES

## Correctness

**Correctness review of `main...HEAD` (tickets #1 to #8)**

I read the full diff and all 8 tickets. The unit suite passes: `python3 -m unittest discover -s tests` ran 260 tests, OK. Every finding below is **ours**, introduced by this diff, unless marked otherwise.

**A note on #3 ("Move status-flow"):** `skills/status-flow` has never existed on `main` in this repository, and `git log --all -- skills/status-flow` is empty. So "passes and fails as before" and "pack rules files keep working unchanged" can't be checked against the old extractor here. The "nothing points to the old skill" test passes because there was nothing there in the first place. Someone needs to diff the new kind against the old pack copy by hand.

### High

1. **Graph files end up in the repository after all.** `skills/implement-spec/SKILL.md` step 8 (not changed by this diff) still says to copy `<runData>/runs/<spec>*` into the integration worktree and commit it, except the state and checks logs. `drive.py diagram` now writes `<spec>-<ticket>-plan.json`, `-proof.json` and `-pr.md` into that folder (`drive.py:441-443`). The SKILL also tells agents to put their extracted graphs there.
   - Failure: with a `runData` inside the repository (the default `.claude/workflow-runs`), every diagram file gets committed into the PR.
   - This breaks #5 ("never in the repository") and the new `docs/decisions.md` entry. Step 8 needs to exclude the diagram files. No test covers step 8.

2. **`skill_overlap.py` reads the wrong core when run as the skills tell you to.** At `skills/writing-for-agents/scripts/skill_overlap.py:29`, `CORE` comes from `os.path.abspath(__file__)`, not `realpath`.
   - `install.sh` links each skill on its own (for example `~/.claude/skills/writing-for-agents -> <core>/skills/writing-for-agents`).
   - Both `writing-for-agents/SKILL.md` and `retro/SKILL.md` run `~/.claude/skills/writing-for-agents/scripts/skill_overlap.py`. From that path, `CORE` works out to `~/.claude`, so the "core" rows become every skill in `~/.claude/skills`. That includes linked pack skills and personal skills, all labelled `core`.
   - Each pack skill then shows twice (once as `core`, once as `pack …`). Each copy pairs with the other at word overlap 1.0 and with every quoted phrase shared, so these false pairs fill the top 10.
   - `drive.py`, `track_record.py` and the retro's own instruction all use the real path. Every test passes `--core`, so the default is never tested. Fix: use `realpath` and add a test that runs through a symlinked skill folder.

3. **A relative or non-package `ast.typescript` setting can't be loaded.** In `skills/diagram/scripts/typescript.mjs:15-18, 24-39`, the lookup returns the saved setting exactly as written. `settings.md` documents it as relative (`{"typescript": "node_modules/typescript"}`).
   - `existsSync(path.join(tsPath, "package.json"))` resolves against the process's working directory, not the repository root.
   - `createRequire(import.meta.url)("node_modules/typescript")` is a bare specifier. Node looks for a package called `node_modules` from the skill's folder and throws `MODULE_NOT_FOUND`.
   - That isn't a `LookupError`, so it surfaces as a stack trace with exit 2.
   - Failure: `ast_tool.py save typescript node_modules/typescript`, then any status-flow or call-tree extract crashes.
   - Fix: resolve the saved value against the repository root before loading it. No test covers loading from a saved setting.

### Medium

4. **A failed release-branch push leaves a release that can't be finished.** `release.sh:73-76` pushes the tag, then `release`, then runs `gh release create`.
   - If the `release` push is rejected (the case `test_never_overwrites_a_release_branch_that_moved_elsewhere` sets up), `set -e` stops the script after the tag is already on origin.
   - There is then no GitHub release. A rerun finds the new tag as `last` and prints "nothing to release", so the script can't recover.
   - Fix: push the tag and `release` in one `git push --atomic`, or push `release` first. Then assert that no tag reached origin in that test. Right now it only checks the exit code and the branch.

5. **Call tree: calls to overloaded functions are dropped silently.** At `skills/diagram/kinds/call-tree/scripts/extract.mjs:72-76`, `calleeOf` takes `symbol.declarations[0]`. For an overloaded function or method, that is the first overload signature, which has no body, so `!bodyOf(decl)` returns `undefined`.
   - Failure: `function f(a: string): void; function f(a: any) { g(); }` means neither `f` nor anything it reaches appears in the graph.
   - A proof diagram would then miss edges. Fix: use the declaration with a body, or `checker.getResolvedSignature(call)?.declaration`.
   - Related, lower severity: node ids are `<file>#<name>` (line 63). Two same-named functions in one file (nested helpers, or object-literal methods versus top-level functions) share one node, and the second one's calls are never followed (line 65).

6. **Status flow draws edges the code doesn't allow.** At `skills/diagram/kinds/status-flow/scripts/extract.mjs:98-117`, every comparison in a function becomes a "from" state and every assignment a "to" state, and the script draws every combination.
   - `if (o.status === "Cancelled") throw …; o.status = "Shipped";` draws `Cancelled -> Shipped`, which the guard forbids.
   - `if (s === "Draft") s = "Review"; else if (s === "Review") s = "Published";` draws a spurious `Draft -> Published`.
   - Either one makes `check.mjs` report a false breach of a `never` rule. The behaviour is documented in `status-flow.md` and may be carried over from the old extractor, which I can't confirm (see the #3 note). It is still wrong for guard clauses.

7. **`track_record.py`: one gh failure stops the whole build.** `gh()` at line 46 calls `sys.exit` on any error. `my_commits` (line 69) and `merged_prs` call it for every work repository.
   - Failure: one repository under `--root` that is empty (409), deleted or renamed, or in an org whose SAML SSO the token isn't authorised for (403, common for work orgs) aborts `build` and `missing`. You get no page at all.
   - Fix: skip and report the repository rather than exiting. Not tested.

8. **`track_record.py`: duplicate clones are double-counted.** `work_repos` (lines 54-64) doesn't deduplicate by slug.
   - Failure: `--root` holding `shop` and `shop-2` (a second clone or a worktree folder, since `.git` can be a file) with the same origin counts every merged PR twice. That inflates output, rework counts, the snapshot and `missing`.

9. **`track_record.py`: origin matching misses common setups.**
   - The `ORIGIN` regex (line 39) only matches `github.com`. An SSH host alias such as `git@github-work:org/repo.git`, which is common exactly where work and personal accounts are separate, makes the work repository vanish silently.
   - `reviews_given` matches `slug in projects` case-sensitively (line 126). If the origin URL's casing differs from GitHub's `nameWithOwner` (for example `acme/shop` against `Acme/Shop`), every review for that repository is dropped silently.

10. **`ast_tool.py find`: a saved choice is ignored whenever one local tool exists.** At `skills/ast/scripts/ast_tool.py:57-61`, a single local tool always wins over the saved one.
    - Failure: in a TypeScript 7 repository, a saved TS 5.x path is never returned. Every extract exits 3 again, so the developer is asked every run, not "once per repository" (#1).

11. **`ast_tool.py`: a broken settings file reads as "no tool".** `chosen()` (lines 52-54) treats any non-zero exit from `settings.py`, including invalid JSON, as "nothing saved". `find` then exits 3 with "no AST tool found" and the real error is hidden.

### Low

12. **`drive.py diagram` doesn't check `--ticket` against the run's tickets** (lines 486-516). A typo writes `s1-12x-plan.json`. Ticket `12` then has no plan diagram and merges without a check.

13. **The check compares files, not the code.** `diagram_problem` (lines 461-471) compares the stored plan and proof files. A proof that matched before later commits (review fixes, merging the integration tip) still passes `checks` and `merge`. This is inherent to the design, but nothing in `drive.py` or the skills says the proof must be re-extracted after later changes.

14. **The "no proof yet" message omits the fix hint.** In `drive.py:467`, when the proof is missing the message leaves out the `fix` text that the mismatch message includes.

15. **`settings.py set` doesn't validate.** `save` (lines 159-170) never runs `problems()` afterwards. It can also replace a whole object, for example `set ast foo` wipes every language, and `set version 2` stores the string `"2"`.

16. **`track_record.py` measurement limits.**
    - `merged_prs` stops at `--limit 1000` without saying so.
    - Rework uses `committedDate`, so a rebase after review marks every commit as rework, and bot or Copilot reviews count as the "first review".
    - Calibration rows in the ledger count towards grades over time.

17. **Snapshot privacy.** Project names in `snapshot.json` are repository names, which can be partner names (#7 says none in the snapshot). This is inherent to "counts per project". Worth one line in the SKILL.

### Tests

- **No test** runs `skill_overlap.py` with its default `--core` (item 2). Same for `typescript.mjs` loading from a saved setting (item 3), the state `release.sh` leaves after a rejected `release` push (item 4), overloaded functions (item 5), guard-clause or cross-branch status flows (item 6), and duplicate clones or a gh failure in `track_record` (items 7 and 8).
- **No tautological assertions.** The drive mismatch test, compare tests, track-record signal tests and release fast-forward test would each go red if the behaviour they name broke.
- **Nothing extra.** I found no test or file that isn't asked for by a ticket.
- **Weakened safeguards:** none. The diff has no deletions of checks, guards or tests. In `test_release.py`, only the setUp line changed (it now also creates `release`); no expectation was weakened. `cmd_merge`'s new diagram check runs before the `--approved` gate, so `--approved` can't skip it, as #5 requires.

ISSUES

Summary: Standards 1 hard (duplicated `main_checkout` in ast_tool.py) plus judgement calls; Spec 0 blocking, worst is #6's manual real-install run still open; Correctness 17 findings, worst is diagram files being committed with the run records at step 8 (and skill_overlap.py reading the wrong core through the install symlink).
