"""Tests for skills/track-record/scripts/track_record.py, on throwaway repos and fake gh output. All data is fictional."""
import datetime
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(CORE, "skills", "track-record", "scripts", "track_record.py")
spec = importlib.util.spec_from_file_location("track_record", SCRIPT)
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)

LOGIN = "dev-fictional"


def git(repo, *args, name="t", email="t@example.com", date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email)
    if date:
        env.update(GIT_AUTHOR_DATE=f"{date}T12:00:00", GIT_COMMITTER_DATE=f"{date}T12:00:00")
    subprocess.run(["git", "-C", repo, *args], check=True, env=env, capture_output=True)


def make_repo(root, name, origin):
    repo = os.path.join(root, name)
    os.makedirs(repo)
    git(repo, "init", "-q")
    git(repo, "remote", "add", "origin", origin)
    return repo


def commit(repo, msg, name, email, date):
    with open(os.path.join(repo, "f.txt"), "a") as f:
        f.write(msg + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg, name=name, email=email, date=date)


def write_map(root, project, areas):
    """A fictional knowledge map in the format knowledge.py reads."""
    lines = [f"# Knowledge map: {project}", ""]
    for name, level in areas:
        lines += [f"## {name}", "", f"- Level: {level}", f"- Paths: src/{name.lower()}/",
                  f"- 2026-05-01: ({level}) explained the {name.lower()} flow", ""]
    os.makedirs(os.path.join(root, "knowledge"), exist_ok=True)
    with open(os.path.join(root, "knowledge", f"{project}.md"), "w") as f:
        f.write("\n".join(lines))


def write_ledger(repo, rows):
    """A fictional grade ledger where ledger.py looks for it: <runData>/grades.md."""
    os.makedirs(os.path.join(repo, ".claude", "workflow-runs"))
    with open(os.path.join(repo, ".claude", "workflow.json"), "w") as f:
        json.dump({"version": 1, "committed": False, "tracker": {"kind": "github"}, "checks": "true",
                   "docs": {"glossary": "GLOSSARY.md", "adr": "docs/adr"}, "runData": ".claude/workflow-runs",
                   "verifySkill": "verify-shop"}, f)
    table = "".join(f"| {date} | {run} | spec-to-pr | none | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3.00 | {grade} | {dev} |  | counted | a \\| b |\n"
                    for date, run, grade, dev in rows)
    text = tr.ledger.header().replace("\n## Level changes", table + "\n## Level changes")
    with open(os.path.join(repo, ".claude", "workflow-runs", "grades.md"), "w") as f:
        f.write(text)


class FakeGh:
    """Answers the gh calls track_record makes, from fixed fictional JSON."""

    def __init__(self, emails=(), prs=(), reviews=()):
        self.emails, self.prs, self.reviews, self.calls = list(emails), list(prs), list(reviews), []

    def __call__(self, *args):
        self.calls.append(args)
        if args[:2] == ("api", "user"):
            return {"login": LOGIN}
        if args[0] == "api" and "/commits" in args[1]:
            return [[{"commit": {"author": {"email": e}}} for e in self.emails]]
        if args[:2] == ("pr", "list"):
            return self.prs
        if args[:2] == ("api", "graphql"):
            return {"data": {"user": {"contributionsCollection": {"pullRequestReviewContributions": {
                "nodes": self.reviews, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}}
        raise AssertionError(f"unexpected gh call {args}")


def pr(number, merged, title="Fictional change", reviews=(), commits=(), files=("src/a.py",), slug="acme-fictional/shop"):
    return {"number": number, "title": title, "url": f"https://github.com/{slug}/pull/{number}",
            "mergedAt": f"{merged}T10:00:00Z",
            "reviews": [{"author": {"login": who}, "state": state, "submittedAt": f"{when}Z"} for who, state, when in reviews],
            "commits": [{"committedDate": f"{when}Z"} for when in commits],
            "files": [{"path": f} for f in files]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.out = os.path.join(self.root, "report")
        self.saved_gh = tr.gh
        os.environ["TRACK_RECORD_DIR"] = self.out
        os.environ["KNOWLEDGE_DIR"] = os.path.join(self.root, "knowledge")

    def tearDown(self):
        tr.gh = self.saved_gh
        os.environ.pop("TRACK_RECORD_DIR", None)
        os.environ.pop("KNOWLEDGE_DIR", None)
        self.tmp.cleanup()

    def use(self, fake):
        tr.gh = fake
        return fake

    def work_repo(self):
        repo = make_repo(self.root, "shop", "git@github.com:acme-fictional/shop.git")
        commit(repo, "one", "Dev Fictional", "dev@work.example.com", "2026-03-02")
        return repo

    def build(self):
        tr.build(self.root)
        with open(os.path.join(self.out, "snapshot.json")) as f:
            return json.load(f)

    def page(self):
        with open(os.path.join(self.out, "report.html")) as f:
            return f.read()


class Scope(Base):
    def test_only_repos_owned_by_someone_else_are_work(self):
        make_repo(self.root, "shop", "git@github.com:acme-fictional/shop.git")
        make_repo(self.root, "notes", "https://github.com/dev-fictional/notes.git")
        os.makedirs(os.path.join(self.root, "not-a-repo"))
        work = tr.work_repos(self.root, LOGIN)
        self.assertEqual([(os.path.basename(r), slug) for r, slug in work], [("shop", "acme-fictional/shop")])

    def test_commits_count_every_email_github_links_to_the_developer_and_no_one_elses(self):
        repo = make_repo(self.root, "shop", "git@github.com:acme-fictional/shop.git")
        commit(repo, "one", "Dev Fictional", "dev@work.example.com", "2026-03-02")
        commit(repo, "two", "Dev F", "dev@home.example.com", "2026-04-03")
        commit(repo, "three", "Other Person", "other@example.com", "2026-04-04")
        self.use(FakeGh(emails=["dev@work.example.com", "dev@home.example.com", "dev@work.example.com"]))
        self.assertEqual(tr.my_commits(repo, "acme-fictional/shop", LOGIN), ["2026-03-02", "2026-04-03"])


class Failures(Base):
    def test_a_repository_gh_cannot_read_is_skipped_and_named(self):
        self.work_repo()
        make_repo(self.root, "gone", "git@github.com:acme-fictional/gone.git")

        class OneRepoFails(FakeGh):
            def __call__(self, *args):
                if any("acme-fictional/gone" in a for a in args):
                    raise tr.GhError("gh api repos/acme-fictional/gone/commits failed: HTTP 404")
                return super().__call__(*args)

        self.use(OneRepoFails(emails=["dev@work.example.com"], prs=[pr(1, "2026-03-05")]))
        err = io.StringIO()
        with redirect_stderr(err):
            snap = self.build()
        self.assertEqual(snap["output"], {"2026-03": {"shop": 1}})
        self.assertIn("skipped acme-fictional/gone", err.getvalue())


class Signals(Base):
    def test_merged_prs_per_month_and_rework_rate_match_gh(self):
        self.work_repo()
        self.use(FakeGh(emails=["dev@work.example.com"], prs=[
            pr(1, "2026-03-05", reviews=[("rev-a", "COMMENTED", "2026-03-03T09:00:00")],
               commits=["2026-03-02T09:00:00", "2026-03-04T09:00:00"]),
            pr(2, "2026-03-20", reviews=[("rev-a", "CHANGES_REQUESTED", "2026-03-18T09:00:00"),
                                         ("rev-b", "APPROVED", "2026-03-19T09:00:00")],
               commits=["2026-03-17T09:00:00"]),
            pr(3, "2026-04-02", reviews=[(LOGIN, "COMMENTED", "2026-03-31T09:00:00")], commits=["2026-04-01T09:00:00"]),
        ]))
        snap = self.build()
        self.assertEqual(snap["output"], {"2026-03": {"shop": 2}, "2026-04": {"shop": 1}})
        self.assertEqual(snap["quality"], {"reviewed_prs": 2, "reworked_prs": 1, "rework_rate": 0.5,
                                           "changes_requested_prs": 1})

    def test_reviews_per_month_use_each_reviews_own_date(self):
        self.work_repo()

        def review(when, author="rev-a", repo="acme-fictional/shop", number=7):
            return {"occurredAt": f"{when}T10:00:00Z", "pullRequest": {
                "url": f"https://github.com/{repo}/pull/{number}", "author": {"login": author},
                "repository": {"nameWithOwner": repo}}}

        self.use(FakeGh(emails=["dev@work.example.com"], reviews=[
            review("2026-03-30"), review("2026-04-02"), review("2026-04-20", number=8),
            review("2026-04-21", author=LOGIN), review("2026-04-22", repo="dev-fictional/notes"),
        ]))
        self.assertEqual(self.build()["reviews"], {"2026-03": {"shop": 1}, "2026-04": {"shop": 2}})

    def test_reviews_are_read_a_year_at_a_time_and_every_page(self):
        repo = make_repo(self.root, "shop", "git@github.com:acme-fictional/shop.git")
        commit(repo, "one", "Dev Fictional", "dev@work.example.com", "2024-06-01")

        def node(when, number):
            return {"occurredAt": f"{when}T10:00:00Z", "pullRequest": {
                "url": f"https://github.com/acme-fictional/shop/pull/{number}", "author": {"login": "rev-a"},
                "repository": {"nameWithOwner": "acme-fictional/shop"}}}

        class Paged(FakeGh):
            def __call__(self, *args):
                if args[:2] != ("api", "graphql"):
                    return super().__call__(*args)
                self.calls.append(args)
                first = "from=2024-06-01T00:00:00Z" in args
                if first and "after=c1" not in args:
                    nodes, more = [node("2024-07-01", 1)], True
                elif first:
                    nodes, more = [node("2024-08-01", 2)], False
                elif "from=2025-06-01T00:00:00Z" in args:
                    nodes, more = [node("2025-07-01", 3)], False
                else:
                    nodes, more = [], False
                return {"data": {"user": {"contributionsCollection": {"pullRequestReviewContributions": {
                    "nodes": nodes, "pageInfo": {"hasNextPage": more, "endCursor": "c1" if more else None}}}}}}

        fake = self.use(Paged(emails=["dev@work.example.com"]))
        data = tr.collect(self.root, today=datetime.date(2026, 6, 1))
        self.assertEqual([r["date"] for r in data["reviews"]], ["2024-07-01", "2024-08-01", "2025-07-01"])
        windows = sorted({a for call in fake.calls if call[:2] == ("api", "graphql") for a in call if a.startswith("from=")})
        self.assertEqual(windows, ["from=2024-06-01T00:00:00Z", "from=2025-06-01T00:00:00Z", "from=2026-06-01T00:00:00Z"])

    def test_breadth_lists_areas_at_can_explain_or_above_and_folders_prs_changed(self):
        self.work_repo()
        write_map(self.root, "shop", [("Baskets", "can explain"), ("Search", "followed it"), ("Checkout", "can teach")])
        self.use(FakeGh(emails=["dev@work.example.com"], prs=[
            pr(1, "2026-03-05", files=["src/a.py", "infra/stack.ts", "README.md"]),
            pr(2, "2026-03-06", files=["src/b.py", "docs/x.md"]),
        ]))
        b = tr.breadth(tr.collect(self.root))
        self.assertEqual([(a["project"], a["area"], a["level"]) for a in b["areas"]],
                         [("shop", "Baskets", "can explain"), ("shop", "Checkout", "can teach")])
        self.assertEqual(b["folders"], {"shop": ["docs", "infra", "src"]})

    def test_grades_over_time_and_blind_grade_agreement_match_the_ledger(self):
        repo = self.work_repo()
        write_ledger(repo, [("2026-04-01", "#2", "F", "D"), ("2026-05-01", "#3", "A", "C"), ("2026-06-01", "#4", "C", "")])
        self.use(FakeGh(emails=["dev@work.example.com"]))
        snap = self.build()
        self.assertEqual(snap["grades"], [{"date": "2026-04-01", "project": "shop", "grade": "F", "dev": "D"},
                                          {"date": "2026-05-01", "project": "shop", "grade": "A", "dev": "C"},
                                          {"date": "2026-06-01", "project": "shop", "grade": "C", "dev": ""}])
        self.assertEqual(snap["agreement"], {"blind_graded": 2, "within_one_letter": 1})


class Snapshot(Base):
    def test_snapshot_keeps_counts_areas_and_impact_but_no_titles_keys_people_or_pr_paths(self):
        repo = self.work_repo()
        write_map(self.root, "shop", [("Baskets", "can explain")])
        write_ledger(repo, [("2026-04-01", "#2", "B", "B")])
        self.use(FakeGh(emails=["dev@work.example.com"], prs=[
            pr(41, "2026-03-05", title="ABC-123 Fix the fictional basket for Partnerco",
               reviews=[("rev-a", "APPROVED", "2026-03-04T09:00:00")], files=["src/a.py"]),
        ]))
        tr.impact("https://github.com/acme-fictional/shop/pull/41", "Cut basket errors for every shopper")
        snap = self.build()
        text = json.dumps(snap)
        for leak in ("ABC-123", "fictional basket", "Partnerco", "rev-a", "/pull/", "github.com", "acme-fictional",
                     "explained the baskets flow", "src"):
            self.assertNotIn(leak, text)
        self.assertEqual(snap["areas"], [{"project": "shop", "area": "Baskets", "level": "can explain"}])
        self.assertEqual(snap["impact"], [{"project": "shop", "month": "2026-03", "text": "Cut basket errors for every shopper"}])


class Page(Base):
    def test_page_is_self_contained_with_inline_svg_and_every_pr_linked(self):
        repo = self.work_repo()
        write_map(self.root, "shop", [("Baskets", "can explain")])
        write_ledger(repo, [("2026-04-01", "#2", "B", "C")])
        self.use(FakeGh(emails=["dev@work.example.com"], prs=[
            pr(1, "2026-03-05", title="Stop <script>alert(1)</script> in names",
               reviews=[("rev-a", "CHANGES_REQUESTED", "2026-03-04T09:00:00")], commits=["2026-03-04T12:00:00"]),
            pr(2, "2026-04-05"),
        ]))
        self.build()
        page = self.page()
        self.assertEqual(page.count("<svg"), 2)  # why: no reviews here, so only output and grades are charts
        self.assertIn("2026-03 · shop: 1 merged PRs</title>", page)
        for banned in ("<script", "<link", "src=", "url(", "@import"):
            self.assertNotIn(banned, page.lower())
        self.assertIn("Stop &lt;script&gt;", page)
        for n in (1, 2):
            self.assertIn(f'href="https://github.com/acme-fictional/shop/pull/{n}"', page)
        self.assertIn("In the snapshot", page)


class Impact(Base):
    def test_missing_lists_prs_with_no_impact_line_until_one_is_added(self):
        self.work_repo()
        self.use(FakeGh(emails=["dev@work.example.com"], prs=[pr(1, "2026-03-05"), pr(2, "2026-03-06")]))
        url1, url2 = (f"https://github.com/acme-fictional/shop/pull/{n}" for n in (1, 2))
        self.assertEqual([p["url"] for p in tr.missing(self.root)], [url1, url2])
        tr.impact(url1, "Made refunds same-day")
        self.assertEqual([p["url"] for p in tr.missing(self.root)], [url2])
        tr.impact(url2, "Fictional fix two")
        tr.impact(url1, "Made refunds same-day for every shopper")
        self.assertEqual(tr.impact_lines(), {url1: "Made refunds same-day for every shopper", url2: "Fictional fix two"})
        self.assertEqual(tr.missing(self.root), [])


if __name__ == "__main__":
    unittest.main()
