#!/usr/bin/env python3
"""Context guard: nudge Claude to hand off to a fresh session once the context gets large.

Runs on UserPromptSubmit and PostToolUse. Reads the current context size from the latest
assistant turn in the session transcript (input + cached tokens), and once it passes
THRESHOLD tells Claude to write a handoff and offer a fresh session at the next natural
checkpoint. It nudges once at THRESHOLD, then once every STEP above it, so it doesn't repeat
on every turn. If the context drops back below THRESHOLD (after a compaction), it resets.

Never blocks anything: any error means it stays silent.
"""

import json
import os
import sys

THRESHOLD = 150_000
STEP = 50_000
TAIL_BYTES = 2_000_000
STATE_DIR = os.path.expanduser("~/.claude/hooks/state")


def context_tokens(transcript_path):
    size = os.path.getsize(transcript_path)
    with open(transcript_path, "rb") as handle:
        handle.seek(max(0, size - TAIL_BYTES))
        lines = handle.read().decode("utf-8", errors="ignore").splitlines()
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = (entry.get("message") or {}).get("usage")
        if entry.get("type") == "assistant" and usage:
            return (
                usage.get("input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
            )
    return None


def main():
    payload = json.load(sys.stdin)
    transcript_path = payload.get("transcript_path")
    session_id = payload.get("session_id") or "unknown"
    event = payload.get("hook_event_name") or "PostToolUse"
    if not transcript_path or not os.path.exists(transcript_path):
        return

    tokens = context_tokens(transcript_path)
    if tokens is None:
        return

    os.makedirs(STATE_DIR, exist_ok=True)
    state_path = os.path.join(STATE_DIR, f"context-guard-{session_id}.json")
    try:
        with open(state_path, encoding="utf-8") as handle:
            last_band = json.load(handle).get("band", 0)
    except (OSError, json.JSONDecodeError):
        last_band = 0

    if tokens < THRESHOLD:
        if last_band:
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump({"band": 0}, handle)
        return

    band = THRESHOLD + ((tokens - THRESHOLD) // STEP) * STEP
    if band <= last_band:
        return
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump({"band": band}, handle)

    thousands = tokens // 1000
    context = (
        f"Context guard: this session's context is about {thousands}k tokens, past the "
        f"{THRESHOLD // 1000}k point where mistakes become more likely. Don't stop mid-step. "
        "At the next natural checkpoint (a phase or layer boundary, a finished ticket, or the end "
        "of this turn's work), tell the user the context size and offer to continue in a fresh "
        "session: write a handoff first (the running workflow's own handoff, or the handoff "
        "skill where a repo has one), "
        "then offer the fresh session with a short brief pointing at it. If the user has already "
        "said to keep going here, just mention the size once."
    )
    print(
        json.dumps(
            {
                "systemMessage": f"Context guard: about {thousands}k tokens in this session.",
                "hookSpecificOutput": {"hookEventName": event, "additionalContext": context},
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
