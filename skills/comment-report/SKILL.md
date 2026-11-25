---
name: comment-report
description: Report every code comment in a repository or folder that should go, with what would replace it. Runs only when the developer types /comment-report, optionally followed by a path.
disable-model-invocation: true
---

<!-- Based on Matt Pocock's "comments considered harmful" prompt (x.com/mattpocockuk/status/2123798388227403983, 20 Nov 2026), turned from delete-and-file into report-only. -->

Sort every comment in the target into one of four groups and say what should replace it. This skill writes nothing: no edits, no issues, no ADRs. The developer acts on the report.

The rule behind it is `codebase-design`'s "Code that explains itself": names, types and tests carry the meaning, and a comment stays only for a reason the code can't show, as one line starting `why:`.

Settings come from `python3 ~/.claude/skills/setup-workflow/scripts/settings.py` (called `settings.py` below); without project settings, `get` prints nothing and the defaults below apply.

## 1. List the comments

The target is the path the developer gave, or the whole repository. From the repository root, run `python3 ~/.claude/skills/setup-workflow/scripts/ratchet.py comments <path>`. It prints `path:line` for every comment line in tracked files, and already leaves out `why:` comments, shebangs, licence headers, tool directives, docstrings and generated files. Read each comment with the code around it.

With more than about 150 comment lines, split the list by folder and give each part to a worker subagent (the agent `settings.py get workerAgent` names, or the core's `worker`), all in parallel. Paste each worker the four groups below and ask for its rows back in its reply. Each one is read only.

## 2. Sort each comment

Every listed comment lands in exactly one group:

- **Tautology**: repeats what the code already shows. Replace it with nothing, or with whatever would make the code show it: a rename, an extracted function or constant with an honest name, a narrower type (a union of statuses rather than a string), or a test whose name states the rule. Name the replacement.
- **Excuse**: covers for a hacky implementation ("temporary", "hack", "workaround", "should really…"). The comment lets the hack spread. Draft a one-paragraph issue to fix the code itself.
- **Stale**: refers to code, behaviour or plans that no longer exist. Check the claim against the code before calling it stale, and say what it contradicts.
- **Decision Record**: records a decision no one could see from the code. When it is hard to reverse, surprising and a real trade-off, it belongs in an ADR (the folder `settings.py get adr` names); otherwise it stays as a one-line `why:` comment. If a test could prove the reason, propose the test instead.

A commented-out block of code is Stale.

## 3. Report

Write the report in chat, grouped by the four groups, one row per comment: `path:line`, the comment (first line only), and the replacement. Put the drafted issues and proposed ADRs after the tables. End with the totals per group and the lines removing the Tautology, Stale and Excuse comments would shed.

If the repository has the comment ratchet (`.ratchet/comments.json`), say that once the fixes land, `ratchet.py lower` brings its baseline down. Offer to make the changes, file the issues or write the ADRs, and do each only on the developer's yes.
