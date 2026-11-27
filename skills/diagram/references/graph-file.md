# Graph file

The JSON every diagram kind's extractor writes and every diagram script reads. Back to [the skill](../SKILL.md).

```json
{
  "title": "Document workflow",
  "groups": [{"id": "editing", "label": "Editing"}],
  "nodes": [
    {"id": "draft", "label": "Draft", "group": "editing"},
    {"id": "review", "label": "In review", "group": "editing", "mark": "added"}
  ],
  "edges": [{"from": "draft", "to": "review", "label": "submit", "mark": "added"}]
}
```

- **groups** (optional): boxes drawn round nodes. `id` is required; `label` defaults to the id.
- **nodes**: `id` is required and unique; `label` defaults to the id; `group` names a group's id.
- **edges**: `from` and `to` name node ids; `label` is optional. One edge per `from` and `to` pair, which is how `compare.mjs` matches edges: the same pair with another label or mark is a changed edge.
- **mark** (optional on each): `added` (green), `removed` (red, dashed), `unchanged` (grey, the default) or `mismatch` (amber).

A plan graph marks the planned edits on the code as it is. A proof graph marks what changed between before and after. `mismatch` marks an item where the code and the plan disagree.
