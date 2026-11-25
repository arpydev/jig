---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

<!-- Local fork of mattpocock/skills research (MIT, see ../../LICENSE-mattpocock-skills). upstream/ holds the version it was taken from. Every local change is listed under "Local changes" at the end. -->

Spin up a **background agent** to do the research, so you keep working while it reads. Start it with a fresh context window.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

## Local changes

Taken 2026-11-23 from github.com/mattpocock/skills at commit abeeaf9 (`skills/engineering/research/`, MIT licence), first into another project and moved to the core on 2026-11-25. When upstream changes, diff it against `upstream/`, carry the changes in, keep the changes below, then replace `upstream/`.

| Date | Change | Why | Upstream? |
|---|---|---|---|
| 2026-11-25 | None beyond the fork comment and this section | Moved to the core as it was | Local only |
