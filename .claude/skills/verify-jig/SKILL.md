---
name: verify-jig
description: How to check that each feature of this project works, with a feature map of where its code and tests are. Read it before exploring the code, when testing a change, or when planning which tests cover an area.
---

# verify-jig

Read the feature's row before exploring. If a run had to explore or found a row wrong, the retro fixes the row.

## Feature map

| Feature | Code | Tests | How to check |
|---|---|---|---|
| implement-spec driver | `skills/implement-spec/scripts/drive.py` | `tests/test_drive.py` | `python3 -m unittest tests.test_drive` |
| Grade ledger and transcripts | `skills/grade-run/scripts/` | `tests/test_grade_run.py` | `python3 -m unittest tests.test_grade_run` |
| Retro lookups | `skills/retro/scripts/lookups.py` | `tests/test_lookups.py` | `python3 -m unittest tests.test_lookups` |
| Workflow settings, detect, ratchet | `skills/setup-workflow/scripts/` | `tests/test_setup_workflow.py`, `tests/test_ratchet.py` | `python3 -m unittest tests.test_setup_workflow tests.test_ratchet` |
| Ticket publishing | `skills/to-tickets/scripts/publish.py` | `tests/test_publish_tickets.py` | `python3 -m unittest tests.test_publish_tickets` |
| Knowledge map | `skills/knowledge-map/scripts/knowledge.py` | `tests/test_knowledge.py` | `python3 -m unittest tests.test_knowledge` |
| Hooks | `hooks/`, `scripts/hooks.py` | `tests/test_hooks.py` | `python3 -m unittest tests.test_hooks` |
| Install, update, release | `install.sh`, `update.sh`, `uninstall.sh`, `release.sh` | `tests/test_update.py`, `tests/test_release.py` | `python3 -m unittest tests.test_update tests.test_release` |
| Skill references and no-regression | `scripts/skill_refs.py`, `scripts/no_regression.py` | `tests/test_no_regression.py` | `python3 -m unittest tests.test_no_regression` |
| Website skill groups | `website/src/lib/groups.ts` | `tests/test_website_groups.py` | `python3 -m unittest tests.test_website_groups` (the build's group rule, without Node) |
| Website | `website/` | the Astro build | see the full suite below |

## Full end-to-end suite

Run once on the integration branch, in implement-spec's step 7. The project's `checks` setting stays the fast per-ticket check and doesn't build the website.

1. `python3 -m unittest discover -s tests && python3 skills/setup-workflow/scripts/ratchet.py check`
2. The website build, on the Node version in `website/.nvmrc`: `cd website && nvm use && npm ci && npm run build`. The website keeps its npm lockfile.

## Routes still to map

Move each route into a feature's row the first time a run touches it.

- (none found)
