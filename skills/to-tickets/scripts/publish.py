#!/usr/bin/env python3
"""Publish approved ticket drafts as GitHub issues, blockers first.

Usage: publish.py <drafts.md> --repo <owner/name> [--label ready-for-agent] [--parent <number>] [--dry-run]

The drafts file holds one ticket per `# <NN>: <Title>` heading, in dependency order, each body in
to-tickets' issue template. In its `## Blocked by` section, `#<NN>` names another draft. The script:
creates the label if missing, publishes each ticket (reusing an issue with the same title, so it is
safe to rerun), rewrites draft numbers to real issue numbers, sets GitHub's own blocked-by links, and
adds each issue as a sub-issue of --parent. It prints one line per ticket.
"""
import argparse
import json
import re
import subprocess
import sys

HEADING = re.compile(r"^# (\d+): (.+)$", re.M)
SECTION = re.compile(r"^## Blocked by\n(.*?)(?=^## |\Z)", re.M | re.S)
REF = re.compile(r"#(\d+)\b")


def parse(text):
    """Return [(draft number, title, body, [blocker draft numbers])] in file order."""
    heads = list(HEADING.finditer(text))
    tickets = []
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = re.sub(r"\n-{3,}\s*$", "", text[head.end():end].strip()).strip()
        section = SECTION.search(body)
        blockers = [int(n) for n in REF.findall(section.group(1))] if section else []
        tickets.append((int(head.group(1)), head.group(2).strip(), body, blockers))
    return tickets


def rewrite(body, real):
    """Swap draft numbers for real issue numbers inside the Blocked by section only."""
    def swap(section):
        return REF.sub(lambda m: f"#{real.get(int(m.group(1)), m.group(1))}", section.group(0))
    return SECTION.sub(swap, body)


def check_order(tickets):
    seen = set()
    for number, title, _, blockers in tickets:
        late = [b for b in blockers if b not in seen]
        if late:
            sys.exit(f"draft {number} ({title}) is blocked by {late}, which come later or don't exist")
        seen.add(number)


def gh(*args, data=None):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout) if data else out.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--label", default="ready-for-agent")
    ap.add_argument("--parent", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tickets = parse(open(args.drafts).read())
    if not tickets:
        sys.exit("no `# <NN>: <Title>` headings found")
    check_order(tickets)

    existing = {i["title"]: i["number"] for i in gh(
        "issue", "list", "-R", args.repo, "--state", "all", "--limit", "1000", "--json", "number,title", data=True)}
    labels = {l["name"] for l in gh("label", "list", "-R", args.repo, "--limit", "500", "--json", "name", data=True)}
    if args.label not in labels:
        print(f"label {args.label}: {'would create' if args.dry_run else 'created'}")
        if not args.dry_run:
            gh("label", "create", args.label, "-R", args.repo, "--color", "0E8A16",
               "--description", "Ready for an agent to pick up")

    real = {}
    for number, title, body, blockers in tickets:
        body = rewrite(body, real)
        if title in existing:
            real[number] = existing[title]
            state = "exists"
        elif args.dry_run:
            real[number] = f"new-{number}"
            print(f"{number}: would create '{title}', blocked by {[real[b] for b in blockers]}")
            continue
        else:
            url = gh("issue", "create", "-R", args.repo, "--title", title, "--body", body, "--label", args.label)
            real[number] = int(url.rsplit("/", 1)[-1])
            state = "created"
        line = f"{number}: #{real[number]} {state}"
        if args.dry_run:
            print(f"{line}, would link blocked by {[real[b] for b in blockers]}")
            continue
        for blocker in blockers:
            line += link(args.repo, f"issues/{real[number]}/dependencies/blocked_by", "issue_id", real[blocker],
                         f"blocked by #{real[blocker]}")
        if args.parent:
            line += link(args.repo, f"issues/{args.parent}/sub_issues", "sub_issue_id", real[number],
                         f"sub-issue of #{args.parent}")
        print(line)


def link(repo, path, field, number, label):
    """Set one native link; an existing link or an unsupported API is reported, not fatal."""
    try:
        issue_id = gh("api", f"repos/{repo}/issues/{number}", "--jq", ".id")
        gh("api", "-X", "POST", f"repos/{repo}/{path}", "-F", f"{field}={issue_id}")
        return f", {label}"
    except RuntimeError as err:
        return f", {label} not set ({err.splitlines()[0] if str(err) else 'error'})"


if __name__ == "__main__":
    main()
