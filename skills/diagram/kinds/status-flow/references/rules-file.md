# Rules file

The JSON a person writes to say how a status flow must behave. `check.mjs` reads it with a graph file and checks every rule. Back to [the kind](status-flow.md).

The rules name states by their node id in the graph file, which is the enum member or union string as written in the code.

## Example

A graph file the extractor wrote for a ticket workflow:

```json
{
  "title": "TicketStatus in ticket.ts",
  "nodes": [
    {"id": "Open"}, {"id": "InProgress"}, {"id": "Resolved"}, {"id": "Closed"}
  ],
  "edges": [
    {"from": "Open", "to": "InProgress", "label": "start"},
    {"from": "InProgress", "to": "Resolved", "label": "resolve"},
    {"from": "Resolved", "to": "Open", "label": "reopen"},
    {"from": "Resolved", "to": "Closed", "label": "close"}
  ]
}
```

Its rules file:

```json
{
  "start": ["Open"],
  "flags": {"resolved": ["Resolved"]},
  "rules": [
    {"name": "resolved-before-closed", "says": "A ticket is resolved before it is closed", "never": "Closed", "unless": ["resolved"]},
    {"name": "can-close", "says": "A ticket can be closed", "reach": "Closed"},
    {"name": "can-reopen", "says": "A resolved ticket can be reopened", "reach": "Open"}
  ]
}
```

## Fields

- **start** (required): the states a new item can begin in. The check walks breadth-first from each.
- **flags** (optional): facts a path picks up on the way, each with the states that set it. A flag holds once the path has passed through one of its states, the state it arrives at included, and stays set for the rest of the path.
- **rules** (required), each with a unique `name`, an optional `says` (one plain sentence, printed when it breaks) and exactly one of:
  - `never`: a state no path may reach. With `unless`, a list of flags, a path may reach it once it holds every one of them.
  - `reach`: a state some path from a start state must reach.

## What the check prints

- **Exit 0**: `<n> rules hold`.
- **Exit 1**: one line per broken rule. A `never` rule gives the shortest path that breaks it, as state labels: `broken resolved-before-closed (A ticket is resolved before it is closed): Open -> Closed`. A `reach` rule says the state is never reached.
- **Exit 2**: the graph or rules file doesn't hold together, such as a rule naming an unknown state or flag.

Edges marked `removed` are not followed, so a proof graph is checked as the code now stands.
