## Ticket #8: deploy the website only on releases

I built ticket #8 test-first on `claude/1-8-8`, in two commits: 8d22fe7 and 6991df4. `claude/1-8` was already merged in ("Already up to date"). `drive.py checks 1-8 8` passes: 260 tests and the ratchet.

**Changes**
- `/Volumes/Development/personal/jig/.claude/worktrees/1-8-8/release.sh` now runs this right after it pushes the tag:
  `g push --quiet origin "$next^{commit}:refs/heads/release"`
  This is a plain push, so git refuses it unless it is a fast-forward. It runs after the dry-run exit. The header comment says what it does.
- `/Volumes/Development/personal/jig/.claude/worktrees/1-8-8/website/vercel.json` is new: `{"git": {"deploymentEnabled": {"main": false}}}`.
- `/Volumes/Development/personal/jig/.claude/worktrees/1-8-8/tests/test_release.py`:
  - `setUp` now also creates `release` at v1.0.0 on the fake origin, the same as the one-off setup.
  - There are 4 new tests and one extended test.
- `/Volumes/Development/personal/jig/.claude/worktrees/1-8-8/README.md`: the Website section now says:
  - the production branch is `release`, and `release.sh` moves it to each release's tag;
  - nobody commits to `release` by hand;
  - `vercel.json` turns off deploys from `main`.

**Acceptance criteria**

| Criterion | Proof |
|---|---|
| A release pushes the tag's commit to `release` | `test_release_branch_points_at_the_new_tag` (red before the code change, then green) |
| A dry run doesn't touch `release` | `test_dry_run_changes_nothing`, extended: `release` stays at v1.0.0 |
| A second release fast-forwards `release` with no force push | `test_second_release_fast_forwards_release`, plus `test_never_overwrites_a_release_branch_that_moved_elsewhere` (if `release` has diverged, the release fails and `release` is left alone) |
| `vercel.json` turns off deploys from main | `WebsiteDeploys.test_vercel_does_not_deploy_from_main` (red before the file existed) |
| The README names the `release` branch | Checked by reading it, as the ticket says; `test_readme` passes |
| A push to main doesn't deploy, and the next release does | Manual. Not done; see open items |

**Break table** (run by script; both files were restored and checked identical to backups with `cmp`)

| Break | Tests that went red |
|---|---|
| Drop the release push | test_release_branch_points_at_the_new_tag, test_second_release_fast_forwards_release, test_never_overwrites_a_release_branch_that_moved_elsewhere |
| Push `release` before the dry-run exit | test_dry_run_changes_nothing |
| Force-push `release` (`+` refspec) | test_never_overwrites_a_release_branch_that_moved_elsewhere |
| Push `HEAD^` to `release` instead of the tag | test_release_branch_points_at_the_new_tag, test_second_release_fast_forwards_release |
| `vercel.json` `"main": true` | test_vercel_does_not_deploy_from_main |
| `vercel.json` key renamed to `master` | test_vercel_does_not_deploy_from_main |

**Open items**
- **Not handled:** if `release` has diverged, the tag is already pushed by the time the `release` push fails, so `gh release create` never runs and the run stops part-way. The ticket asks for the push after the tag, so I left the order as it is. Checking before tagging would avoid this, but that is a scope decision for you.
- **Workaround:** the first `drive.py checks` failed the comment ratchet, because my two-line header comment took `release.sh` to 12 comments against 11 allowed. Commit 6991df4 cuts it to one line.
- **Orchestrator items (not done by me):**
  - One-off push creating `release` at `v1.1.0` on the real origin, confirmed first.
  - Changing the Vercel production branch from `main` to `release` in the dashboard (the developer's job).
  - The manual check on the next release.
- Nothing was pushed, and `release.sh` was never run against the real origin.

PASS
