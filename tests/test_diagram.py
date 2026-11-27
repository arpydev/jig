import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(CORE, "skills", "diagram")
SCRIPTS = os.path.join(SKILL, "scripts")
FIXTURES = os.path.join(CORE, "tests", "fixtures", "diagram")
SVG = ""


def run(*args):
    return subprocess.run(list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL)


def fixture(name):
    return os.path.join(FIXTURES, name)


def needs_node():
    if not shutil.which("node"):
        raise unittest.SkipTest("node is not installed: the diagram scripts need Node")
    if not os.path.isdir(os.path.join(SKILL, "node_modules", "elkjs")):
        if not shutil.which("pnpm"):
            raise unittest.SkipTest("pnpm is not installed: can't install the diagram skill's elkjs")
        r = run("pnpm", "install", "--frozen-lockfile", "--dir", SKILL)
        if r.returncode:
            raise unittest.SkipTest("pnpm install failed in skills/diagram: " + r.stderr[-300:])


class NodeTest(unittest.TestCase):
    """Runs the diagram scripts, so skips with a reason when Node or pnpm is missing."""

    @classmethod
    def setUpClass(cls):
        needs_node()


def node(script, *args):
    return run("node", os.path.join(SCRIPTS, script), *args)


class RenderTest(NodeTest):
    """render.mjs draws a graph file as one self-contained HTML page."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self.tmp.name, "diagram.html")

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, name="all-marks.json"):
        r = node("render.mjs", fixture(name), self.out)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.out, encoding="utf-8") as f:
            return f.read()

    def test_page_has_inline_svg_and_nothing_external(self):
        html = self.render()
        self.assertIn("<svg", html)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("http", html.lower())
        svg = ET.fromstring(re.search(r"<svg.*</svg>", html, re.S).group(0))
        labels = {t.text for t in svg.iter(SVG + "text")}
        self.assertTrue({"Draft", "In review", "Published", "Archived", "Editing", "submit"} <= labels, labels)

    def test_each_mark_is_drawn_in_its_colour(self):
        svg = ET.fromstring(re.search(r"<svg.*</svg>", self.render(), re.S).group(0))
        colours = {"added": "#2e7d32", "removed": "#c62828", "unchanged": "#757575", "mismatch": "#ef8f00"}
        nodes = {g.get("data-id"): g.find("rect").get("stroke") for g in svg.iter("g") if g.get("class") == "node"}
        self.assertEqual(nodes, {"draft": colours["unchanged"], "review": colours["added"],
                                 "published": colours["mismatch"], "archived": colours["removed"]})
        edges = {(g.get("data-from"), g.get("data-to")): g.find("path").get("stroke")
                 for g in svg.iter("g") if g.get("class") == "edge"}
        self.assertEqual(edges, {("draft", "review"): colours["added"], ("review", "published"): colours["mismatch"],
                                 ("draft", "published"): colours["unchanged"],
                                 ("published", "archived"): colours["removed"]})

    def test_difference_list_names_every_marked_item(self):
        items = re.findall(r'<li data-mark="(\w+)"[^>]*>([^<]*)</li>', self.render())
        self.assertEqual(items, [
            ("added", "added node In review"),
            ("mismatch", "mismatch node Published"),
            ("removed", "removed node Archived"),
            ("added", "added edge Draft -&gt; In review (submit)"),
            ("mismatch", "mismatch edge In review -&gt; Published (approve)"),
            ("removed", "removed edge Published -&gt; Archived"),
        ])

    def test_labels_are_escaped(self):
        path = os.path.join(self.tmp.name, "symbols.json")
        with open(path, "w") as f:
            json.dump({"nodes": [{"id": "a", "label": "x < y & z"}]}, f)
        svg = ET.fromstring(re.search(r"<svg.*</svg>", self.render(path), re.S).group(0))
        self.assertIn("x < y & z", {t.text for t in svg.iter("text")})

    def test_graph_with_no_marks_lists_no_differences(self):
        unmarked = os.path.join(self.tmp.name, "unmarked.json")
        with open(unmarked, "w") as f:
            json.dump({"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"from": "a", "to": "b"}]}, f)
        html = self.render(unmarked)
        self.assertIn("No differences.", html)
        self.assertNotIn("<li", html)


class CompareTest(NodeTest):
    """compare.mjs checks a proof graph against its plan graph."""

    def compare(self, proof):
        return node("compare.mjs", fixture("plan.json"), fixture(proof))

    def test_identical_graphs_pass(self):
        r = self.compare("proof-identical.json")
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)

    def test_extra_edge_fails_and_is_named(self):
        r = self.compare("proof-extra-edge.json")
        self.assertEqual((r.returncode, r.stdout), (1, "extra edge Published -> Draft (withdraw)\n"), r.stderr)

    def test_missing_edge_fails_and_is_named(self):
        r = self.compare("proof-missing-edge.json")
        self.assertEqual((r.returncode, r.stdout), (1, "missing edge In review -> Published (approve)\n"), r.stderr)

    def test_changed_edge_fails_and_is_named(self):
        r = self.compare("proof-changed-edge.json")
        self.assertEqual((r.returncode, r.stdout), (1, "changed edge Draft -> In review: label submit, now send\n"),
                         r.stderr)


class MermaidTest(NodeTest):
    """mermaid.mjs writes a graph as a Mermaid block for a pull request body."""

    def test_fixture_matches_its_snapshot(self):
        r = node("mermaid.mjs", fixture("all-marks.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(fixture("all-marks.mermaid.md"), encoding="utf-8") as f:
            self.assertEqual(r.stdout, f.read())

    def test_quotes_in_labels_are_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "quoted.json")
            with open(path, "w") as f:
                json.dump({"nodes": [{"id": "a", "label": 'Say "hi"'}]}, f)
            r = node("mermaid.mjs", path)
        self.assertIn('n0["Say #quot;hi#quot;"]', r.stdout)


class GraphFileTest(NodeTest):
    """Every script refuses a graph file that doesn't hold together."""

    def check(self, graph):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as f:
                json.dump(graph, f)
            return node("mermaid.mjs", path)

    def test_edge_to_an_unknown_node_is_refused(self):
        r = self.check({"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "ghost"}]})
        self.assertEqual(r.returncode, 2)
        self.assertIn("edge a -> ghost names an unknown node", r.stderr)

    def test_unknown_mark_is_refused(self):
        r = self.check({"nodes": [{"id": "a", "mark": "moved"}]})
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown mark moved", r.stderr)


class PackageTest(unittest.TestCase):
    """The skill installs with pnpm and elkjs is its only runtime dependency."""

    def test_elkjs_is_the_only_dependency_and_pnpm_locks_it(self):
        with open(os.path.join(SKILL, "package.json")) as f:
            package = json.load(f)
        self.assertEqual(list(package.get("dependencies", {})), ["elkjs"])
        self.assertEqual(package.get("devDependencies", {}), {})
        with open(os.path.join(SKILL, "pnpm-lock.yaml")) as f:
            self.assertIn("elkjs", f.read())
        for other in ("package-lock.json", "yarn.lock"):
            self.assertFalse(os.path.exists(os.path.join(SKILL, other)), other)


if __name__ == "__main__":
    unittest.main()
