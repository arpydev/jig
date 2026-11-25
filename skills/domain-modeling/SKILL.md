---
name: domain-modeling
description: Build and sharpen the domain model for a repo while planning or grilling. Challenge terms against the repo's glossary, settle vague words on one name, check claims against the code, and write the glossary and ADRs down as soon as they are settled. Use during a grill, when discussing what a project term means, or when recording or editing a decision record (ADR).
---

<!-- Local fork of mattpocock/skills domain-modeling (MIT, see ../../LICENSE-mattpocock-skills). The upstream/ folder holds the version this fork was taken from. Every local change is listed under "Local changes" at the end. -->

# Domain modeling

Build and sharpen the project's domain model while you design. Challenge terms, make up edge-case scenarios, and write the glossary and decisions down as soon as they are settled. Reading the glossary for vocabulary is something any skill can do. Use this skill when the model changes.

## Where the docs live

The project settings say where the glossary and ADRs are:

```bash
python3 ~/.claude/skills/setup-workflow/scripts/settings.py get docs.glossary
python3 ~/.claude/skills/setup-workflow/scripts/settings.py get docs.adr
```

A path outside the repository keeps them out of git. Before writing there, check that the folder isn't inside a git repository (`git -C <folder> rev-parse` should fail). With no settings, use `GLOSSARY.md` at the repo root and `docs/adr/`.

Then run `python3 ~/.claude/skills/setup-workflow/scripts/settings.py steps domain`. Read each file it prints and load each `skill:<name>`: they say what else belongs in this project's glossary and how to write it, and they win over this skill where they disagree.

What goes where:

- **Glossary:** words for one repo's domain, such as a status, a kind of order or a list in the admin portal.
- **Memory:** how the developer likes to work. Glossary terms don't go in memory.

## During the session

### Challenge against the glossary

When the developer uses a term that conflicts with the glossary, say so straight away: "The glossary defines a check-in as X, but you seem to mean Y. Which is it?"

### Sharpen vague words

When a term is vague or means more than one thing, propose one precise name: "By 'held', do you mean a check-in left Booked with its list fields removed, or a new status?"

### Test with concrete scenarios

When the discussion is about how concepts relate, test the relationships with specific scenarios. Make up edge cases that make the developer say where one concept ends and the next begins.

### Check claims against the code

When the developer says how something works, check whether the code agrees. Raise any contradiction: "The code sends trial orders straight to the warehouse when Review Needed isn't ticked, but you said every trial order is reviewed. Which is right?"

### Update the glossary as you go

When a term is settled, update the glossary then and there. Don't save terms up for later. Use the format in [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md). Tell the developer in one line which term you added or changed.

The glossary holds no implementation detail. It is not a spec, a scratch pad or a place for implementation decisions. Code names (an enum value, a field) can follow a term in backticks so readers can find it, but the definition says what the thing is, not how it is built.

### Offer ADRs sparingly

Offer an ADR only when all three are true:

1. **Hard to reverse:** changing your mind later would cost something real.
2. **Surprising without context:** a later reader will wonder why it was done this way.
3. **A real trade-off:** there were real alternatives, and one was picked for specific reasons.

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md). Ask before writing each ADR.

## Local changes

Taken 2026-11-23 from github.com/mattpocock/skills at commit abeeaf9 (`skills/engineering/domain-modeling/`, MIT licence). When upstream changes, diff it against `upstream/`, carry the changes into these files, keep the changes below, then replace `upstream/`.

| Date | Change | Why | Upstream? |
|---|---|---|---|
| 2026-11-23 | Glossary and ADRs live where the project settings say; a path outside the repository is checked to be outside any git checkout | Team repositories keep them out of git until the team agrees | Local only |
| 2026-11-23 | Glossary vs memory split; project step additions (`domain`) add more, such as a company knowledge base | Three sources would disagree | Local only |
| 2026-11-23 | Ask before each ADR; say which glossary term changed | The developer approves each step | Local only |
| 2026-11-24 | Project-only rules (a company knowledge base, data rules, spelling, `origin/main`) moved to a pack's `domain` step addition | The core holds no company facts | Local only |
