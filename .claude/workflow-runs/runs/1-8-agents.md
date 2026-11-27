# 1-8: implementer agents

Written by `drive.py` from `1-8-state.json`. Integration branch `claude/1-8`, cut from `main` at 02996a2.

Orchestrating sessions: 8d407a7a-2752-4486-9955-882ad00590b6, d1c5cc48-0ed8-4473-9640-b52c136db696, 26083bdd-985f-4f6f-a3ed-9162f5c1037d. Transcripts are in `~/.claude/projects/<project>/<session-id>/subagents/agent-<agent-id>.jsonl`.

| Ticket | Branch | Agent IDs | Base | Status | Merged |
|---|---|---|---|---|---|
| 1 Add the ast skill | claude/1-8-1 | afdea5ad68e5be4ad | 02996a2 | merged | 1b462ed |
| 2 Add the diagram skill: graph file, drawing and comparison | claude/1-8-2 | a7d7871537f0a2880, ac7ef5ce3645b6f03 | 1b462ed | merged | d001f2f |
| 3 Move status-flow into diagram as a kind | claude/1-8-3 | a0822e93437b5aa29 | d001f2f | merged | 60f277a |
| 4 Add a TypeScript call-tree kind | claude/1-8-4 | a19115b68379b0a28 | 60f277a | merged | 9088571 |
| 5 Wire plan and proof diagrams into implement and implement-spec | claude/1-8-5 | a23d8323d9075fa3a | 9088571 | merged | dd25bbd |
| 6 Report skill overlaps when a skill is written and at the retro's step-back | claude/1-8-6 | a1839c8c6072af456, ab2a1e9025426ab0f | dd25bbd | merged | 7f37258 |
| 7 Add the track-record skill | claude/1-8-7 | a5cfa356f343534cf | 7f37258 | merged | 266eacb |
| 8 Deploy the website only on releases, from a release branch | claude/1-8-8 | af099256aa8c5ec08 | 266eacb | merged | 506c2c4 |

Other work (not a ticket):

| Work | Agent ID |
|---|---|
| review-fix | ae3a54d5a48b38341 |
