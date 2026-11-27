## Ticket #7: the track-record skill (branch `claude/1-8-7`, commit `2eafdd6`)

I checked the branch first: it printed `claude/1-8-7`. I merged `claude/1-8` (it was already up to date). `drive.py checks 1-8 7` passes: 256 tests OK and the ratchet is `ok`.

**What I built**
- `skills/track-record/SKILL.md` and `skills/track-record/scripts/track_record.py`. The script uses only the standard library and has `build [--root]`, `missing [--root]` and `impact URL TEXT`. Every gh call goes through `gh()`, which the tests replace.
- It reads the knowledge map by importing `knowledge.py` (`map_path` and `load`). It finds the ledger by running `ledger.py path` and reads the table using `ledger.COLUMNS`. A repo with no workflow settings just has no grades.
- It writes `report.html` and `snapshot.json` to `~/.claude/report/` (or `TRACK_RECORD_DIR`). The page is self-contained: inline SVG stacked bars and a grade chart, using the dataviz palette in light and dark. There are native `<title>` tooltips instead of scripts, and a table view behind each chart where every count links to its PRs. Each section is tagged "In the snapshot" or "Page only".
- `tests/test_track_record.py`: 10 tests. They use throwaway repos, fictional authors with `example.com` emails, fake gh JSON, and a fictional knowledge map and ledger. Nothing was run against real repos, real gh data or `~/.claude/report/`.
- I ran `skill_overlap.py` before creating the skill; no existing skill covers this job.

**Acceptance criteria**
1. Only the work repo is reported: `test_only_repos_owned_by_someone_else_are_work`.
2. Commits under two of the developer's emails count and another author's do not: `test_commits_count_every_email_github_links_to_the_developer_and_no_one_elses`. The developer's emails are the ones GitHub links to their login in that repo (`repos/<slug>/commits?author=<login>`).
3. Merged PRs per month and the rework rate match: `test_merged_prs_per_month_and_rework_rate_match_gh`.
4. Reviews per month use each review's own date: `test_reviews_per_month_use_each_reviews_own_date`, plus `test_reviews_are_read_a_year_at_a_time_and_every_page`.
5. Breadth: `test_breadth_lists_areas_at_can_explain_or_above_and_folders_prs_changed`.
6. Grades and blind-grade agreement: `test_grades_over_time_and_blind_grade_agreement_match_the_ledger`.
7. The snapshot leaks nothing: `test_snapshot_keeps_counts_areas_and_impact_but_no_titles_keys_people_or_pr_paths`. It checks for the ticket key, title, partner name, reviewer login, `/pull/`, `github.com`, the repo owner, evidence text and folder names.
8. `missing` and `impact`: `test_missing_lists_prs_with_no_impact_line_until_one_is_added`.
9. The page has inline SVG, no `<script` and no external links: `test_page_is_self_contained_with_inline_svg_and_every_pr_linked`.
10. Docs and website:
    - README Scripts row, guide table row, glossary "Track record" entry (placed at the end) and a new website group "Your record".
    - `skill_refs.py`: no output, exit 0.
    - `pnpm run build` in `website/` on Node 24 ended: `[build] 31 page(s) built in 463ms` / `[build] Complete!`, exit 0. The built pages include `dist/skills/track-record`.

I also rendered a fictional demo page in the browser and looked at both charts: no label collisions; the last date label on the grade chart was clipped and is now fixed.

**Break table** (each break applied to the script, the test file run, then the script restored from a backup and checked identical)

| Break | Tests that went red |
|---|---|
| own repos counted as work | all 9 that build or collect, including the scope test |
| commits: every author counted | test_commits_count_every_email… |
| commits: only first linked email | test_commits_count_every_email… |
| rework: any commit counts | test_merged_prs_per_month_and_rework_rate… |
| rework: denominator is all PRs | test_merged_prs_per_month_and_rework_rate… |
| rework: own review counts as first | test_merged_prs_per_month_and_rework_rate… (first showed NONE; I added a self-review fixture) |
| changes requested never seen | test_merged_prs_per_month_and_rework_rate… |
| reviews dated by window start | test_reviews_per_month…, test_reviews_are_read_a_year_at_a_time… |
| reviews on own PRs counted | test_reviews_per_month… |
| reviews in non-work repos counted | test_reviews_per_month… |
| reviews: next page not read | test_reviews_are_read_a_year_at_a_time… |
| reviews: one year window only | test_reviews_are_read_a_year_at_a_time… |
| breadth floor at "followed it" | test_breadth… |
| top-level files counted as folders | test_breadth… |
| E counted as a grade letter | test_grades_over_time… |
| agreement on exact match only | test_grades_over_time… |
| Dev column read as the grade | test_grades_over_time… |
| escaped `\|` splits ledger cells | test_grades_over_time…, test_page… |
| snapshot impact keeps the URL | test_snapshot… |
| snapshot impact keeps the title | test_snapshot… |
| snapshot keeps evidence text | test_snapshot… |
| page: no HTML escaping | test_page… |
| page: links without href | test_page… |
| page: bar charts dropped | test_page… (first showed NONE; I added an SVG count and a tooltip assertion) |
| page: snapshot tags dropped | test_page… |
| impact rewrite loses other lines | test_missing… (strengthened with a second URL) |
| `missing` ignores impact lines | test_missing… |

**Outside the ticket's list, and decisions made without asking**
- **Website group fix:** the build already failed on `claude/1-8` because `ast` and `diagram` were in no group. I added both to the "Reference" group so the website criterion could pass. The orchestrator may prefer another group for them.
- **"No external links":** I took this to mean nothing loaded from elsewhere (no `<link`, `src=`, `url(` or `@import`). The page does link to GitHub PRs, because the ticket requires every number to link to its PR. Knowledge and ledger evidence link to the local files with `file://`.
- **Rework rate:** the denominator is PRs that had at least one review from someone else. The developer's own reviews are ignored.
- **Agreement:** grades run A, B, C, D, F with no E, so D and F count as within one letter.
- **Reviews range:** reviews are read a year at a time, from the developer's earliest commit or merged PR in the work repos up to today.
- **Commit dates:** they set that start date and show as each project's active span on the page. They are not shown as counts, since the ticket rules commit counts out.
- **Snapshot contents:** projects are named by repo name only, not the owner. The snapshot includes every map area with its level, not only those at "can explain" or above.

**Open items (process, nothing a code change on this branch would fix)**
- **Node version:** the website build needs Node 22.23.4 or later and the default here is v22.20.0, so I ran it with nvm's v24.21.0 (the website's `.nvmrc` says 24).
- **pnpm and the lockfile:** `website/` has an npm `package-lock.json`. `pnpm run build` creates an untracked `pnpm-lock.yaml`, which I deleted; nothing pnpm-related was committed.
- **verify-jig:** the feature map is empty, so I added no row; the retro owns it.
- **Not tried for real:** the skill has not been run against real gh output. Two flags it relies on are untested outside the fakes: `gh api --paginate --slurp` (needs gh 2.48 or later) and `gh pr list --json` with `reviews`, `commits` and `files`.

PASS
