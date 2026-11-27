#!/usr/bin/env python3
"""The developer's track record across their work repositories, worked out live on each run.

Usage:
  track_record.py build [--root DIR]     write report.html and snapshot.json to the report folder
  track_record.py missing [--root DIR]   list merged PRs with no impact line
  track_record.py impact URL TEXT        add or replace the impact line for one PR

--root defaults to the folder holding the current repository. A repository under it is work when its
origin owner is not the developer's GitHub login (`gh api user`). The report folder is ~/.claude/report
(TRACK_RECORD_DIR overrides it), outside every repository. Sources are read live: git, gh, the knowledge
map through knowledge.py and the grade ledger through ledger.py. The only hand-kept file is impact.md.
Every gh call goes through gh(), so tests can replace it. A repository gh can't read is skipped and named on stderr.
"""
import argparse
import datetime
import html
import importlib.util
import json
import os
import re
import subprocess
import sys

SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def sibling(skill, name):
    """Load another skill's script as a module, so its file format stays its own business."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILLS, skill, "scripts", f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


knowledge = sibling("knowledge-map", "knowledge")
ledger = sibling("grade-run", "ledger")
GRADES = ["A", "B", "C", "D", "F"]  # why: the grader never gives an E, so D and F are one letter apart
ORIGIN = re.compile(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$")


class GhError(Exception):
    pass


def gh(*args):
    """Run gh and return its JSON output."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode:
        raise GhError(f"gh {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return json.loads(r.stdout or "null")


def skip(slug, error):
    print(f"track_record.py: skipped {slug}: {error}", file=sys.stderr)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True).stdout.strip()


def work_repos(root, login):
    """[(path, "owner/name")] for each repository directly under root whose origin owner is not login."""
    out = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.exists(os.path.join(path, ".git")):
            continue
        m = ORIGIN.search(git(path, "remote", "get-url", "origin"))
        if m and m.group(1).lower() != login.lower():
            out.append((path, f"{m.group(1)}/{m.group(2)}"))
    return out


def my_commits(repo, slug, login):
    """Dates (YYYY-MM-DD, oldest first) of local commits under any email GitHub links to login in this repo."""
    pages = gh("api", f"repos/{slug}/commits?author={login}&per_page=100", "--paginate", "--slurp")
    emails = {c["commit"]["author"]["email"].lower() for page in pages or [] for c in page}
    out = []
    for line in git(repo, "log", "--reverse", "--format=%ae %ad", "--date=short").splitlines():
        email, date = line.rsplit(" ", 1)
        if email.lower() in emails:
            out.append(date)
    return out


def report_dir():
    return os.environ.get("TRACK_RECORD_DIR") or os.path.expanduser("~/.claude/report")


def merged_prs(project, slug, login):
    """The developer's merged PRs in one repository, with the facts the signals need."""
    raw = gh("pr", "list", "--repo", slug, "--author", login, "--state", "merged", "--limit", "1000",
             "--json", "number,title,url,mergedAt,reviews,commits,files")
    out = []
    for p in raw or []:
        reviews = sorted(r["submittedAt"] for r in p.get("reviews") or []
                         if (r.get("author") or {}).get("login", "").lower() != login.lower() and r.get("submittedAt"))
        first = reviews[0] if reviews else None
        out.append({
            "project": project, "url": p["url"], "title": p["title"], "merged": p["mergedAt"][:10],
            "reviewed": bool(first),
            "rework": bool(first) and any(c["committedDate"] > first for c in p.get("commits") or []),
            "changes_requested": any(r.get("state") == "CHANGES_REQUESTED" for r in p.get("reviews") or []),
            "folders": sorted({f["path"].split("/")[0] for f in p.get("files") or [] if "/" in f["path"]}),
        })
    return out


REVIEWS_QUERY = """query($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
  user(login: $login) { contributionsCollection(from: $from, to: $to) {
    pullRequestReviewContributions(first: 100, after: $after) {
      nodes { occurredAt pullRequest { url author { login } repository { nameWithOwner } } }
      pageInfo { hasNextPage endCursor } } } } }"""


def reviews_given(login, projects, since, today):
    """One entry per review the developer gave on someone else's PR in a work repo, dated by the review.
    contributionsCollection spans at most a year, so the range is read a year at a time."""
    out, start = [], since
    while start <= today:
        end = min(start + datetime.timedelta(days=364), today)
        after = None
        while True:
            args = ["api", "graphql", "-f", f"query={REVIEWS_QUERY}", "-f", f"login={login}",
                    "-f", f"from={start}T00:00:00Z", "-f", f"to={end}T23:59:59Z"]
            if after:
                args += ["-f", f"after={after}"]
            page = gh(*args)["data"]["user"]["contributionsCollection"]["pullRequestReviewContributions"]
            for n in page["nodes"]:
                pr = n["pullRequest"]
                slug = pr["repository"]["nameWithOwner"]
                author = (pr.get("author") or {}).get("login", "")
                if slug in projects and author.lower() != login.lower():
                    out.append({"project": projects[slug], "url": pr["url"], "date": n["occurredAt"][:10]})
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
        start = end + datetime.timedelta(days=1)
    return out


def collect_prs(root):
    login = gh("api", "user")["login"]
    out = []
    for _, slug in work_repos(root, login):
        try:
            out += merged_prs(slug.split("/")[1], slug, login)
        except GhError as e:
            skip(slug, e)
    return out


def collect(root, today=None):
    """Everything the page and snapshot show, read live from git, gh, the knowledge map and the ledger."""
    login = gh("api", "user")["login"]
    data = {"login": login, "projects": [], "prs": [], "reviews": [], "areas": [], "grades": []}
    for path, slug in work_repos(root, login):
        project = slug.split("/")[1]
        try:
            commits, prs = my_commits(path, slug, login), merged_prs(project, slug, login)
        except GhError as e:
            skip(slug, e)
            continue
        data["projects"].append({"name": project, "slug": slug, "path": path, "commits": commits})
        data["prs"] += prs
        data["areas"] += known_areas(project, path)
        data["grades"] += graded_runs(project, path)
    today = today or datetime.date.today()
    dates = [d for p in data["projects"] for d in p["commits"]] + [p["merged"] for p in data["prs"]]
    since = datetime.date.fromisoformat(min(dates)) if dates else today - datetime.timedelta(days=364)
    data["reviews"] = reviews_given(login, {p["slug"]: p["name"] for p in data["projects"]}, since, today)
    return data


def known_areas(project, repo):
    """Every area in the repo's knowledge map, read through knowledge.py, with its newest evidence line."""
    path = knowledge.map_path(repo)
    out = []
    for name, a in knowledge.load(path).items():
        newest = max(a["evidence"]) if a["evidence"] else (None, "")
        out.append({"project": project, "area": name, "level": a["level"], "evidence": newest, "map": path})
    return out


def graded_runs(project, repo):
    """The rows of the repo's grade ledger, found through ledger.py; none when the repo has no ledger."""
    r = subprocess.run([sys.executable, ledger.__file__, "path", "--repo", repo], capture_output=True, text=True)
    path = r.stdout.strip()
    if r.returncode or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        section = f.read().split("## Grades", 1)[-1].split("\n## ", 1)[0]
    out = []
    for line in section.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) != len(ledger.COLUMNS) or not re.match(r"\d{4}-\d{2}-\d{2}$", cells[0]):
            continue
        row = dict(zip(ledger.COLUMNS, cells))
        out.append({"project": project, "date": row["Date"], "run": row["Run"], "grade": row["Grader"],
                    "dev": row["Dev"], "ledger": path})
    return out


def agreement(grades):
    """How often the developer's blind grade is within one letter of the grader's."""
    blind = [g for g in grades if g["dev"] in GRADES and g["grade"] in GRADES]
    close = [g for g in blind if abs(GRADES.index(g["dev"]) - GRADES.index(g["grade"])) <= 1]
    return {"blind_graded": len(blind), "within_one_letter": len(close)}


def breadth(data):
    """Areas at "can explain" or above, against the top-level folders the developer's merged PRs changed."""
    floor = knowledge.LEVELS.index("can explain")
    areas = [a for a in data["areas"] if a["level"] in knowledge.LEVELS and knowledge.LEVELS.index(a["level"]) >= floor]
    folders = {}
    for p in data["prs"]:
        folders.setdefault(p["project"], set()).update(p["folders"])
    return {"areas": areas, "folders": {k: sorted(v) for k, v in folders.items()}}


def per_month(items, date_key):
    """{month: {project: count}}, months in order."""
    out = {}
    for item in sorted(items, key=lambda i: i[date_key]):
        month = out.setdefault(item[date_key][:7], {})
        month[item["project"]] = month.get(item["project"], 0) + 1
    return out


def quality(prs):
    reviewed = [p for p in prs if p["reviewed"]]
    reworked = [p for p in reviewed if p["rework"]]
    return {"reviewed_prs": len(reviewed), "reworked_prs": len(reworked),
            "rework_rate": round(len(reworked) / len(reviewed), 2) if reviewed else None,
            "changes_requested_prs": sum(p["changes_requested"] for p in prs)}


IMPACT_LINE = re.compile(r"^- (\S+): (.+)$")


def impact_path():
    return os.path.join(report_dir(), "impact.md")


def impact_lines():
    """{PR URL: why it mattered}, from the only hand-kept file."""
    if not os.path.exists(impact_path()):
        return {}
    with open(impact_path(), encoding="utf-8") as f:
        return {m.group(1): m.group(2) for line in f if (m := IMPACT_LINE.match(line.rstrip("\n")))}


def impact(url, text):
    lines = impact_lines()
    lines[url] = " ".join(text.split())
    write(impact_path(), "# Impact\n\nOne line per merged PR on why it mattered, in words for an employer. "
                         "Written by `track_record.py impact`.\n\n" + "".join(f"- {u}: {t}\n" for u, t in lines.items()))


def missing_from(prs):
    have = impact_lines()
    return [p for p in sorted(prs, key=lambda p: p["merged"]) if p["url"] not in have]


def missing(root):
    """Merged PRs with no impact line, oldest first."""
    return missing_from(collect_prs(root))


def snapshot(data):
    """The CV-safe part: counts per month per project, area names, levels, grades and impact lines.
    No PR titles, URLs, ticket keys, other people's names or code."""
    have = impact_lines()
    return {"areas": [{"project": a["project"], "area": a["area"], "level": a["level"]} for a in data["areas"]],
            "impact": [{"project": p["project"], "month": p["merged"][:7], "text": have[p["url"]]}
                       for p in sorted(data["prs"], key=lambda p: p["merged"]) if p["url"] in have],
            "output": per_month(data["prs"], "merged"), "reviews": per_month(data["reviews"], "date"),
            "quality": quality(data["prs"]),
            "grades": [{"date": g["date"], "project": g["project"], "grade": g["grade"], "dev": g["dev"]}
                       for g in sorted(data["grades"], key=lambda g: g["date"])],
            "agreement": agreement(data["grades"])}


# why: the dataviz skill's validated palette (light, dark); the slot order is what keeps adjacent hues apart
SERIES = [("#2a78d6", "#3987e5"), ("#eb6834", "#d95926"), ("#1baf7a", "#199e70"), ("#eda100", "#c98500"),
          ("#e87ba4", "#d55181"), ("#008300", "#0ca30c"), ("#6250d6", "#9085e9"), ("#e34948", "#e66767")]
CSS = """
.viz-root { color-scheme: light; --surface-1: #fcfcfb; --text-primary: #0b0b0b; --text-secondary: #52514e;
  --text-muted: #77766f; --grid: #e4e3df; --border: #d6d5cf; """ + " ".join(
    f"--series-{i + 1}: {light};" for i, (light, _) in enumerate(SERIES)) + """ }
@media (prefers-color-scheme: dark) { .viz-root { color-scheme: dark; --surface-1: #1a1a19; --text-primary: #f0efec;
  --text-secondary: #c3c2b7; --text-muted: #9a998f; --grid: #383835; --border: #4a4945; """ + " ".join(
    f"--series-{i + 1}: {dark};" for i, (_, dark) in enumerate(SERIES)) + """ } }
body { margin: 0; }
.viz-root { background: var(--surface-1); color: var(--text-primary); font: 15px/1.5 system-ui, sans-serif;
  padding: 24px; max-width: 880px; margin: 0 auto; min-height: 100vh; }
h1 { font-size: 24px; margin: 0 0 4px; } h2 { font-size: 18px; margin: 32px 0 4px; }
p, .note { color: var(--text-secondary); margin: 4px 0 12px; }
a { color: inherit; }
.tag { font-size: 12px; border: 1px solid var(--border); border-radius: 4px; padding: 1px 6px; margin-left: 8px;
  color: var(--text-secondary); vertical-align: middle; }
.tiles { display: flex; gap: 16px; flex-wrap: wrap; margin: 12px 0; }
.tile { border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; min-width: 160px; }
.tile .value { font-size: 28px; font-weight: 600; display: block; text-decoration: none; }
.tile .label { font-size: 13px; color: var(--text-secondary); }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--text-secondary); margin: 4px 0; }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
svg text { fill: var(--text-secondary); font-size: 11px; }
svg .grid { stroke: var(--grid); stroke-width: 1; }
svg .seg:hover { opacity: 0.8; }
table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 8px 0; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--grid); vertical-align: top; }
th { color: var(--text-secondary); font-weight: 600; }
details summary { cursor: pointer; color: var(--text-secondary); font-size: 13px; }
"""


def esc(text):
    return html.escape(str(text), quote=True)


def link(url, text):
    return f'<a href="{esc(url)}">{esc(text)}</a>'


def colours(projects):
    """Each project keeps one colour slot, in name order, so a colour always means the same project.
    Past eight projects the rest fold into Other, the eighth slot."""
    names = sorted(projects)
    slots = {n: i for i, n in enumerate(names[:7])}
    for n in names[7:]:
        slots[n] = 7
    return slots, [(n, i) for n, i in slots.items() if i < 7] + ([("Other", 7)] if len(names) > 7 else [])


def legend(keys):
    if len(keys) < 2:
        return ""
    return '<div class="legend">' + "".join(
        f'<span><span class="swatch" style="background: var(--series-{i + 1})"></span>{esc(n)}</span>'
        for n, i in keys) + "</div>"


def months_between(first, last):
    y, m = map(int, first.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= last:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def stacked_bars(counts, slots, noun):
    """Inline SVG: one bar per month, stacked by project, with a native tooltip on each segment."""
    if not counts:
        return f'<p class="note">No {noun} yet.</p>'
    months = months_between(min(counts), max(counts))
    w, h, left, bottom, top = 720, 200, 32, 24, 16
    peak = max(sum(c.values()) for c in counts.values())
    step = max(1, -(-peak // 4))
    ceiling = step * -(-peak // step)
    band = (w - left) / len(months)
    bar = min(32, band * 0.6)
    y = lambda v: top + (h - top - bottom) * (1 - v / ceiling)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(noun)} per month">']
    for v in range(0, ceiling + 1, step):
        out.append(f'<line class="grid" x1="{left}" x2="{w}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                   f'<text x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    every = max(1, len(months) // 12)
    for i, month in enumerate(months):
        x = left + band * i + (band - bar) / 2
        if i % every == 0:
            out.append(f'<text x="{x + bar / 2:.1f}" y="{h - 6}" text-anchor="middle">{month}</text>')
        base = 0
        stack = sorted((counts.get(month) or {}).items(), key=lambda kv: slots[kv[0]])
        for j, (project, n) in enumerate(stack):
            y0, y1 = y(base), y(base + n)
            gap = 2 if j else 0
            height = max(0.0, y0 - y1 - gap)
            r = min(4, height / 2, bar / 2) if j == len(stack) - 1 else 0
            path = (f"M{x:.1f},{y1 + height:.1f} v{-(height - r):.1f} q0,{-r} {r},{-r} h{bar - 2 * r:.1f} "
                    f"q{r},0 {r},{r} v{height - r:.1f} z")
            out.append(f'<path class="seg" d="{path}" fill="var(--series-{slots[project] + 1})">'
                       f'<title>{esc(month)} · {esc(project)}: {n} {esc(noun)}</title></path>')
            base += n
        if len(months) <= 18 and base:
            out.append(f'<text x="{x + bar / 2:.1f}" y="{y(base) - 4:.1f}" text-anchor="middle">{base}</text>')
    return "\n".join(out) + "</svg>"


def grade_chart(grades):
    """Inline SVG: the grader's letter per graded run over time, with the developer's blind grade beside it."""
    if not grades:
        return '<p class="note">No graded runs in these repositories yet.</p>'
    w, h, left, top, bottom = 720, 180, 32, 12, 28
    rows = sorted(grades, key=lambda g: g["date"])
    x = lambda i: left + 40 + (w - left - 80) * (i / max(1, len(rows) - 1))
    y = lambda letter: top + (h - top - bottom) * GRADES.index(letter) / (len(GRADES) - 1)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Grades over time">']
    for letter in GRADES:
        out.append(f'<line class="grid" x1="{left}" x2="{w}" y1="{y(letter):.1f}" y2="{y(letter):.1f}"/>'
                   f'<text x="{left - 8}" y="{y(letter) + 4:.1f}" text-anchor="end">{letter}</text>')
    graded = [(i, g) for i, g in enumerate(rows) if g["grade"] in GRADES]
    if len(graded) > 1:
        points = " ".join(f"{x(i):.1f},{y(g['grade']):.1f}" for i, g in graded)
        out.append(f'<polyline points="{points}" fill="none" stroke="var(--series-1)" stroke-width="2"/>')
    every = max(1, len(rows) // 8)
    for i, g in enumerate(rows):
        if i % every == 0:
            out.append(f'<text x="{x(i):.1f}" y="{h - 4}" text-anchor="middle">{esc(g["date"])}</text>')
    for i, g in graded:
        out.append(f'<circle cx="{x(i):.1f}" cy="{y(g["grade"]):.1f}" r="5" fill="var(--series-1)" '
                   f'stroke="var(--surface-1)" stroke-width="2"><title>{esc(g["date"])} · {esc(g["project"])} '
                   f'{esc(g["run"])}: grader {esc(g["grade"])}</title></circle>')
        if g["dev"] in GRADES:
            out.append(f'<circle cx="{x(i) + 8:.1f}" cy="{y(g["dev"]):.1f}" r="4" fill="var(--surface-1)" '
                       f'stroke="var(--series-2)" stroke-width="2"><title>{esc(g["date"])} · your blind grade '
                       f'{esc(g["dev"])}</title></circle>')
    return "\n".join(out) + "</svg>"


def tag(in_snapshot):
    return f'<span class="tag">{"In the snapshot" if in_snapshot else "Page only"}</span>'


def month_table(items, date_key, label):
    """The table view behind a chart: every count with the links it is made of."""
    rows = {}
    for item in sorted(items, key=lambda i: i[date_key]):
        rows.setdefault((item[date_key][:7], item["project"]), []).append(item)
    body = "".join(f"<tr><td>{esc(m)}</td><td>{esc(p)}</td><td>{len(its)}</td><td>"
                   + ", ".join(link(i["url"], i.get("title") or i["url"].rsplit("/", 1)[-1]) for i in its)
                   + "</td></tr>" for (m, p), its in rows.items())
    return (f"<details><summary>Table view: every {esc(label)} with its link</summary><table><tr><th>Month</th>"
            f"<th>Project</th><th>Count</th><th>Evidence</th></tr>{body}</table></details>")


def pr_list(prs, anchor, label):
    if not prs:
        return ""
    return (f'<details id="{anchor}"><summary>{esc(label)}: {len(prs)} PRs with their links</summary><ul>'
            + "".join(f"<li>{link(p['url'], p['title'])} ({esc(p['merged'])}, {esc(p['project'])})</li>"
                      for p in sorted(prs, key=lambda p: p["merged"])) + "</ul></details>")


def render(data, today):
    snap = snapshot(data)
    slots, keys = colours([p["name"] for p in data["projects"]])
    q = snap["quality"]
    reworked = [p for p in data["prs"] if p["rework"]]
    changes = [p for p in data["prs"] if p["changes_requested"]]
    b = breadth(data)
    agree = snap["agreement"]
    have = impact_lines()
    rate = f"{round(q['rework_rate'] * 100)}%" if q["rework_rate"] is not None else "n/a"
    parts = [
        f"<h1>Track record</h1><p>{esc(data['login'])}, worked out on {today} from git, gh, the knowledge map and "
        f"the grade ledger across {len(data['projects'])} work repositories"
        + "".join(f"{'; ' if i else ': '}{esc(p['name'])}" + (f" (your commits {p['commits'][0][:7]} to {p['commits'][-1][:7]})"
                  if p["commits"] else "") for i, p in enumerate(data["projects"])) + ". Every number links to its evidence. "
        "The snapshot (snapshot.json) keeps only counts, area names, levels, grades and impact lines.</p>",
        f"<h2>Output{tag(True)}</h2><p>Merged PRs per month, stacked by project.</p>",
        legend(keys), stacked_bars(snap["output"], slots, "merged PRs"), month_table(data["prs"], "merged", "merged PR"),
        f"<h2>Reviewing{tag(True)}</h2><p>Reviews given on other people's PRs, dated by each review.</p>",
        legend(keys), stacked_bars(snap["reviews"], slots, "reviews"), month_table(data["reviews"], "date", "review"),
        f"<h2>Quality{tag(True)}</h2><p>Rework is a PR with commits pushed after its first review, "
        "out of the PRs that had a review.</p><div class=\"tiles\">"
        f'<div class="tile"><a class="value" href="#reworked">{rate}</a><span class="label">rework rate '
        f'({q["reworked_prs"]} of {q["reviewed_prs"]} reviewed PRs)</span></div>'
        f'<div class="tile"><a class="value" href="#changes">{q["changes_requested_prs"]}</a>'
        '<span class="label">PRs that got "changes requested"</span></div></div>',
        pr_list(reworked, "reworked", "Reworked"),
        pr_list(changes, "changes", "Changes requested"),
        f"<h2>Breadth{tag(True)}</h2><p>Knowledge-map areas at \"can explain\" or above, each linked to its map "
        "and dated by its newest evidence. The folders are page only.</p>",
        "<table><tr><th>Project</th><th>Area</th><th>Level</th><th>Newest evidence</th></tr>" + "".join(
            f"<tr><td>{esc(a['project'])}</td><td>{esc(a['area'])}</td><td>{esc(a['level'])}</td><td>"
            f"{link('file://' + a['map'], a['evidence'][0] or 'none')} {esc(a['evidence'][1])}</td></tr>"
            for a in b["areas"]) + "</table>",
        "<table><tr><th>Project</th><th>Top-level folders your merged PRs changed</th></tr>" + "".join(
            f"<tr><td>{esc(p)}</td><td>{esc(', '.join(f))}</td></tr>" for p, f in b["folders"].items()) + "</table>",
        f"<h2>Independence{tag(True)}</h2><p>The grader's letter for each graded run (filled dots) and your blind "
        "grade beside it (hollow).</p>",
        legend([("Grader", 0), ("Your blind grade", 1)]), grade_chart(data["grades"]),
        f'<div class="tiles"><div class="tile"><a class="value" href="#grades">{agree["within_one_letter"]} of '
        f'{agree["blind_graded"]}</a><span class="label">blind grades within one letter of the grader\'s</span></div></div>',
        '<details><summary>Table view: every graded run with its ledger</summary><table id="grades"><tr><th>Date</th>'
        "<th>Project</th><th>Run</th><th>Grader</th><th>Yours</th></tr>" + "".join(
            f"<tr><td>{link('file://' + g['ledger'], g['date'])}</td><td>{esc(g['project'])}</td><td>{esc(g['run'])}</td>"
            f"<td>{esc(g['grade'])}</td><td>{esc(g['dev'])}</td></tr>"
            for g in sorted(data["grades"], key=lambda g: g["date"])) + "</table></details>",
        f"<h2>Impact{tag(True)}</h2><p>Why each PR mattered, in your words, from {esc(impact_path())}. "
        f"{len(missing_from(data['prs']))} merged PRs have no line yet.</p><ul>" + "".join(
            f"<li>{link(p['url'], p['merged'][:7] + ' ' + p['project'])}: {esc(have[p['url']])}</li>"
            for p in sorted(data["prs"], key=lambda p: p["merged"]) if p["url"] in have) + "</ul>",
        "<p class=\"note\">Left out on purpose: time to merge (it measures reviewers), lines and commit counts, "
        "escaped defects and cycle time (they need tracker work items).</p>",
    ]
    return ('<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>Track record</title>'
            f"<style>{CSS}</style></head><body><main class=\"viz-root\">" + "\n".join(parts) + "</main></body></html>\n")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def build(root):
    data = collect(root)
    out = report_dir()
    write(os.path.join(out, "snapshot.json"), json.dumps(snapshot(data), indent=2) + "\n")
    write(os.path.join(out, "report.html"), render(data, datetime.date.today().isoformat()))
    return data


def default_root():
    common = git(os.getcwd(), "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        sys.exit("track_record.py: not in a git repository; give --root")
    return os.path.dirname(os.path.dirname(common.rstrip("/")))


def main(argv=None):
    ap = argparse.ArgumentParser(description="The developer's track record across their work repositories.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "missing"):
        sub.add_parser(name).add_argument("--root")
    imp = sub.add_parser("impact")
    imp.add_argument("url")
    imp.add_argument("text")
    args = ap.parse_args(argv)
    if args.cmd == "impact":
        impact(args.url, args.text)
        print(f"recorded the impact line for {args.url} in {impact_path()}")
        return
    root = os.path.abspath(args.root or default_root())
    try:
        run(args.cmd, root)
    except GhError as e:
        sys.exit(f"track_record.py: {e}")


def run(cmd, root):
    if cmd == "build":
        data = build(root)
        gap = len(missing_from(data["prs"]))
        print(f"wrote {os.path.join(report_dir(), 'report.html')} and snapshot.json: {len(data['projects'])} work "
              f"repositories, {len(data['prs'])} merged PRs, {gap} with no impact line")
    else:
        for p in missing(root):
            print(f"{p['url']} | {p['merged']} | {p['project']} | {p['title']}")


if __name__ == "__main__":
    main()
