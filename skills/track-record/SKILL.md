---
name: track-record
description: The developer's own track record across their work repositories, worked out from git, gh, the knowledge map and the grade ledger, written as a local HTML page and a CV-safe snapshot. Use when the developer asks for their track record, what they have done or how their work holds up, or wants to add why a PR mattered.
---

# Track record

A record of the developer's work, worked out from evidence on each run, for the developer and fine to show a manager. Every number on the page links to its evidence: the PR, the ledger row, the dated knowledge line. Nothing a source already holds is stored.

`scripts/track_record.py` (relative to this skill's folder) does the work and writes to `~/.claude/report/`, outside every repository:

- `track_record.py build [--root DIR]`: write `report.html` and `snapshot.json`. `--root` defaults to the folder holding the current repository. A repository under it is work when its `origin` owner is not the developer's GitHub login, so personal projects drop out with no list to keep.
- `track_record.py missing [--root DIR]`: merged PRs with no impact line.
- `track_record.py impact URL TEXT`: add or replace the impact line for one PR in `impact.md`, the only hand-kept file.

## Steps

1. Run `build`. Tell the developer where the page is and what it counted.
2. Run `missing`. For each PR it lists, ask the developer for one line on why it mattered, in words they would say to an employer. Offer a draft from the PR title only when they ask for one. Any PR can be skipped. Record each answer with `impact`.
3. If any line was added, run `build` again so the page and snapshot carry it.

Done when the page is rebuilt and every PR `missing` listed has a line or was skipped.

## What the page shows

- **Output**: merged PRs per month, stacked by project.
- **Breadth**: knowledge-map areas at "can explain" or above, against the top-level folders the merged PRs changed.
- **Reviewing**: reviews given on other people's PRs per month, dated by each review.
- **Quality**: rework rate (reviewed PRs with commits pushed after the first review) and PRs that got "changes requested".
- **Independence**: grades over time, and how often the developer's blind grade is within one letter of the grader's.

Left out on purpose: time to merge (it measures reviewers), lines and commit counts, and escaped defects and cycle time (they need tracker work items).

## The snapshot

`snapshot.json` is rewritten on each run so the record outlives access to an employer's repositories. It holds only counts per month per project, area names, levels, grades and impact lines: no PR titles, URLs, ticket keys, other people's names, partner names or code. Impact lines go in it word for word, so keep them free of those too; the page marks which parts are in it. Project names are repository names; when one names a partner, map its `owner/repo` to a neutral name in `~/.claude/report/aliases.json` (for example `{"acme/partnerco-shop": "retail site"}`) and the snapshot uses that name.
