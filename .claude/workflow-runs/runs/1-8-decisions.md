# 1-8: decisions made without asking

- 2026-11-27 11:07: Run named 1-8: loose issues with no spec issue; blockers taken from each issue's 'Blocked by' text because the GitHub dependencies API returned none. Why: drive.py needs a run name and the native blocker links are empty
- 2026-11-27 11:07: Kept new-skill folders (skills/ast, skills/diagram, skills/track-record, website/vercel.json) as touches despite the not-a-path warnings. Why: they are the folders each ticket creates
- 2026-11-27 11:26: Orchestrator reviewed skills/diagram/SKILL.md against writing-for-agents for #2 AC6 and found it fine. Why: the implementer could only self-review
- 2026-11-27 12:20: #5's implementer adds the merged-graph writer in skills/diagram/scripts. Why: compare.mjs only reports differences; the plan diagram and PR Mermaid block need current + expected marked, and #5 is the first consumer
- 2026-11-27 12:52: #6 fix 1 scoped to a README Scripts-table test only. Why: the report's other ISSUES are the orchestrator's PR paste and process notes (test-first order, seams), which no code change fixes
- 2026-11-27 14:05: Graded #1-#5 as calibration and #6-#8 as counted. Why: first five graded runs calibrate; the grader was never more generous than the developer's blind grade (harsher by one letter on #2, #6, #7, #8), so no rubric change and calibration ends after five
- 2026-11-27 14:08: Redacted workplace pack and project names from the committed copies of the #4 and #6 reports. Why: arpydev/jig is public; the originals stay in runData
