import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAGRAM = os.path.join(CORE, "skills", "diagram")
KIND = os.path.join(DIAGRAM, "kinds", "status-flow")
EXTRACT = os.path.join(KIND, "scripts", "extract.mjs")
CHECK = os.path.join(KIND, "scripts", "check.mjs")
FIXTURES = os.path.join(CORE, "tests", "fixtures", "diagram", "status-flow")
TS_CACHE = os.path.join(tempfile.gettempdir(), "jig-test-typescript-5")


def run(*args, cwd=None):
    return subprocess.run(list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=cwd)


def fixture(name):
    return os.path.join(FIXTURES, name)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def needs_node():
    if not shutil.which("node"):
        raise unittest.SkipTest("node is not installed: the status-flow scripts need Node")


def typescript5():
    """A real TypeScript 5 compiler in a cached temp folder, never in the kind's package.json."""
    needs_node()
    path = os.path.join(TS_CACHE, "node_modules", "typescript")
    if not os.path.isfile(os.path.join(path, "package.json")):
        if not shutil.which("pnpm"):
            raise unittest.SkipTest("pnpm is not installed: can't install a TypeScript compiler for the fixture repo")
        os.makedirs(TS_CACHE, exist_ok=True)
        r = run("pnpm", "add", "typescript@5", "--dir", TS_CACHE)
        if r.returncode:
            raise unittest.SkipTest("pnpm couldn't install typescript@5: " + r.stderr[-300:])
    return path


def needs_renderer():
    if not os.path.isdir(os.path.join(DIAGRAM, "node_modules", "elkjs")):
        if not shutil.which("pnpm"):
            raise unittest.SkipTest("pnpm is not installed: can't install the diagram skill's elkjs")
        r = run("pnpm", "install", "--frozen-lockfile", "--dir", DIAGRAM)
        if r.returncode:
            raise unittest.SkipTest("pnpm install failed in skills/diagram: " + r.stderr[-300:])


class FixtureRepo(unittest.TestCase):
    """A throwaway git repository holding a TypeScript state machine, with TypeScript 5 in its node_modules."""

    typescript = True

    @classmethod
    def setUpClass(cls):
        needs_node()
        cls.ts = typescript5() if cls.typescript else None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        run("git", "init", "-q", self.root)
        if self.ts:
            os.makedirs(os.path.join(self.root, "node_modules"))
            os.symlink(self.ts, os.path.join(self.root, "node_modules", "typescript"))

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name, text=None, source=None):
        path = os.path.join(self.root, name)
        if source:
            shutil.copy(fixture(source), path)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        return path

    def extract(self, name, states, *args):
        return run("node", EXTRACT, os.path.join(self.root, name), "--states", states, *args)

    def graph(self, name, states, *args):
        r = self.extract(name, states, *args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)


class ExtractTest(FixtureRepo):
    """extract.mjs reads a state machine out of TypeScript and writes a graph file."""

    def test_methods_become_edges_labelled_with_the_method(self):
        self.add("keeps-rule.ts", source="keeps-rule.ts")
        self.assertEqual(self.graph("keeps-rule.ts", "TicketStatus"), read_json(fixture("ticket-graph.json")))

    def test_a_list_of_allowed_states_adds_an_edge_from_each(self):
        self.add("breaks-rule.ts", source="breaks-rule.ts")
        edges = {(e["from"], e["to"]): e.get("label") for e in self.graph("breaks-rule.ts", "TicketStatus")["edges"]}
        self.assertEqual(edges[("Open", "Closed")], "close")
        self.assertEqual(edges[("Resolved", "Closed")], "close")

    def test_extracted_graph_is_drawn_by_the_shared_renderer(self):
        needs_renderer()
        self.add("keeps-rule.ts", source="keeps-rule.ts")
        graph, page = os.path.join(self.root, "graph.json"), os.path.join(self.root, "graph.html")
        r = self.extract("keeps-rule.ts", "TicketStatus", "--out", graph)
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)
        r = run("node", os.path.join(DIAGRAM, "scripts", "render.mjs"), graph, page)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(page, encoding="utf-8") as f:
            html = f.read()
        drawn = set(re.findall(r'<g class="edge" data-from="(\w+)" data-to="(\w+)"', html))
        self.assertEqual(drawn, {("Open", "InProgress"), ("InProgress", "Resolved"), ("Resolved", "Open"),
                                 ("Closed", "Open"), ("Resolved", "Closed")})

    def test_a_table_of_events_on_a_string_union_labels_each_edge(self):
        self.add("document.ts", "\n".join([
            'export type DocState = "draft" | "review" | "published";',
            "export const next: Record<DocState, Record<string, DocState>> = {",
            '  draft: { submit: "review" },',
            '  review: { approve: "published", reject: "draft" },',
            "  published: {},",
            "};",
        ]))
        graph = self.graph("document.ts", "DocState")
        self.assertEqual([n["id"] for n in graph["nodes"]], ["draft", "review", "published"])
        self.assertEqual(graph["edges"], [{"from": "draft", "to": "review", "label": "submit"},
                                          {"from": "review", "to": "published", "label": "approve"},
                                          {"from": "review", "to": "draft", "label": "reject"}])

    def test_a_table_of_allowed_states_draws_unlabelled_edges(self):
        self.add("document.ts", "\n".join([
            "export enum Doc { Draft, Review, Published }",
            "export const allowed = {",
            "  [Doc.Draft]: [Doc.Review],",
            "  [Doc.Review]: [Doc.Published, Doc.Draft],",
            "  [Doc.Published]: [],",
            "};",
        ]))
        self.assertEqual(self.graph("document.ts", "Doc")["edges"], [
            {"from": "Draft", "to": "Review"}, {"from": "Review", "to": "Published"}, {"from": "Review", "to": "Draft"}])

    def test_a_status_set_without_a_check_is_warned_about_not_drawn(self):
        self.add("document.ts", "\n".join([
            'export type DocState = "draft" | "archived";',
            "export function archive(doc: { status: DocState }) {",
            '  doc.status = "archived";',
            "}",
        ]))
        r = self.extract("document.ts", "DocState")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["edges"], [])
        self.assertIn("archive sets status to archived without checking the status first", r.stderr)

    def test_another_field_name_is_followed_with_field(self):
        self.add("document.ts", "\n".join([
            'export type DocState = "draft" | "review";',
            "export function submit(doc: { stage: DocState; status: DocState }) {",
            '  if (doc.stage !== "draft") throw new Error("not a draft");',
            '  doc.stage = "review";',
            "}",
        ]))
        self.assertEqual(self.graph("document.ts", "DocState", "--field", "stage")["edges"],
                         [{"from": "draft", "to": "review", "label": "submit"}])

    def test_an_unknown_states_type_is_refused(self):
        self.add("keeps-rule.ts", source="keeps-rule.ts")
        r = self.extract("keeps-rule.ts", "OrderState")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no enum or string union type named OrderState", r.stderr)


class CompilerLookupTest(FixtureRepo):
    """The compiler comes from the ast lookup in the fixture repo; the kind bundles none."""

    typescript = False

    def fake_typescript(self, version):
        d = os.path.join(self.root, "node_modules", "typescript")
        os.makedirs(d)
        with open(os.path.join(d, "package.json"), "w") as f:
            json.dump({"name": "typescript", "version": version}, f)

    def test_no_compiler_in_the_repository_relays_the_lookup(self):
        self.add("keeps-rule.ts", source="keeps-rule.ts")
        r = self.extract("keeps-rule.ts", "TicketStatus")
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("no typescript AST tool found", r.stderr)

    def test_typescript_7_asks_for_a_typescript_5_path(self):
        self.fake_typescript("7.0.1")
        self.add("keeps-rule.ts", source="keeps-rule.ts")
        r = self.extract("keeps-rule.ts", "TicketStatus")
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("TypeScript 7.0.1 has no stable JS API", r.stderr)
        self.assertIn("TypeScript 5.x", r.stderr)
        self.assertIn("--typescript <path>", r.stderr)

    def test_a_typescript_5_path_is_used_in_a_typescript_7_repository(self):
        self.fake_typescript("7.0.1")
        self.add("keeps-rule.ts", source="keeps-rule.ts")
        r = self.extract("keeps-rule.ts", "TicketStatus", "--typescript", typescript5())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), read_json(fixture("ticket-graph.json")))

    def test_the_kind_bundles_no_typescript(self):
        package = read_json(os.path.join(KIND, "package.json"))
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            self.assertNotIn("typescript", package.get(section, {}))
        self.assertFalse(os.path.exists(os.path.join(KIND, "node_modules", "typescript")))


class CheckTest(unittest.TestCase):
    """check.mjs walks a graph file breadth-first from the start states and checks each rule."""

    @classmethod
    def setUpClass(cls):
        needs_node()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def check(self, graph, rules):
        graph = graph if isinstance(graph, str) else self.write("graph.json", graph)
        rules = rules if isinstance(rules, str) else self.write("rules.json", rules)
        return run("node", CHECK, graph, rules)

    def test_rules_hold_on_the_graph_that_keeps_them(self):
        r = self.check(fixture("ticket-graph.json"), fixture("rules.json"))
        self.assertEqual((r.returncode, r.stdout), (0, "2 rules hold\n"), r.stderr)

    def test_a_broken_rule_is_named_with_its_shortest_path(self):
        graph = read_json(fixture("ticket-graph.json"))
        graph["edges"].append({"from": "Open", "to": "Closed", "label": "close"})
        r = self.check(graph, fixture("rules.json"))
        self.assertEqual((r.returncode, r.stdout), (
            1, "broken resolved-before-closed (A ticket is resolved before it is closed): Open -> Closed\n"), r.stderr)

    def test_a_flag_set_earlier_on_the_path_lets_a_later_step_through(self):
        graph = {"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                 "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}, {"from": "a", "to": "c"}]}
        rules = {"start": ["b"], "flags": {"seen-b": ["b"]},
                 "rules": [{"name": "via-b", "says": "c only after b", "never": "c", "unless": ["seen-b"]}]}
        self.assertEqual(self.check(graph, rules).returncode, 0)
        rules["start"] = ["a"]
        r = self.check(graph, rules)
        self.assertEqual((r.returncode, r.stdout), (1, "broken via-b (c only after b): a -> c\n"))

    def test_a_never_rule_without_unless_fails_on_any_path(self):
        graph = {"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c", "label": "Gone"}],
                 "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]}
        r = self.check(graph, {"start": ["a"], "rules": [{"name": "no-c", "says": "Never gone", "never": "c"}]})
        self.assertEqual((r.returncode, r.stdout), (1, "broken no-c (Never gone): a -> b -> Gone\n"))

    def test_the_shortest_breaking_path_is_reported(self):
        graph = {"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                 "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "a", "to": "c"}]}
        rules = {"start": ["a"], "flags": {"via-b": ["b"]}, "rules": [{"name": "no-c", "never": "c"}]}
        r = self.check(graph, rules)
        self.assertEqual((r.returncode, r.stdout), (1, "broken no-c: a -> c\n"))

    def test_an_unreachable_state_breaks_a_reach_rule(self):
        graph = read_json(fixture("ticket-graph.json"))
        graph["edges"] = [e for e in graph["edges"] if e["to"] != "Closed"]
        r = self.check(graph, fixture("rules.json"))
        self.assertEqual((r.returncode, r.stdout), (1, "broken can-close (A ticket can be closed): Closed is never reached\n"))

    def test_removed_edges_are_not_followed(self):
        graph = read_json(fixture("ticket-graph.json"))
        graph["edges"].append({"from": "Open", "to": "Closed", "label": "close", "mark": "removed"})
        self.assertEqual(self.check(graph, fixture("rules.json")).returncode, 0)

    def test_a_rule_naming_an_unknown_state_is_refused(self):
        rules = read_json(fixture("rules.json"))
        rules["rules"][1]["reach"] = "Shipped"
        r = self.check(fixture("ticket-graph.json"), rules)
        self.assertEqual(r.returncode, 2)
        self.assertIn("rule can-close names unknown state Shipped", r.stderr)

    def test_unless_naming_an_unknown_flag_is_refused(self):
        rules = read_json(fixture("rules.json"))
        rules["rules"][0]["unless"] = ["approved"]
        r = self.check(fixture("ticket-graph.json"), rules)
        self.assertEqual(r.returncode, 2)
        self.assertIn("rule resolved-before-closed names unknown flag approved", r.stderr)


class FixturePipelineTest(FixtureRepo):
    """The rules pass on the fixture that keeps them and fail on the one that breaks them, straight from the code."""

    def pipeline(self, source):
        self.add(source, source=source)
        graph = os.path.join(self.root, "graph.json")
        r = self.extract(source, "TicketStatus", "--out", graph)
        self.assertEqual(r.returncode, 0, r.stderr)
        return run("node", CHECK, graph, fixture("rules.json"))

    def test_the_version_that_keeps_the_rule_passes(self):
        self.assertEqual(self.pipeline("keeps-rule.ts").returncode, 0)

    def test_the_version_that_breaks_the_rule_fails_on_it(self):
        r = self.pipeline("breaks-rule.ts")
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken resolved-before-closed", r.stdout)


class DocsTest(unittest.TestCase):
    """The kind's references match what the scripts accept, and the core never points at the old skill."""

    def test_the_documented_rules_file_loads_and_is_checked(self):
        needs_node()
        with open(os.path.join(KIND, "references", "rules-file.md"), encoding="utf-8") as f:
            blocks = re.findall(r"```json\n(.*?)```", f.read(), re.S)
        self.assertEqual(len(blocks), 2, "rules-file.md has one example graph and one example rules file")
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for name, block in zip(("graph.json", "rules.json"), blocks):
                paths.append(os.path.join(d, name))
                with open(paths[-1], "w") as f:
                    f.write(block)
            r = run("node", CHECK, *paths)
        self.assertEqual((r.returncode, r.stdout), (0, "3 rules hold\n"), r.stderr)

    def test_the_diagram_skill_lists_the_kind(self):
        with open(os.path.join(DIAGRAM, "SKILL.md"), encoding="utf-8") as f:
            kinds = f.read().split("## Kinds", 1)[1].split("\n## ", 1)[0]
        self.assertIn("kinds/status-flow/references/status-flow.md", kinds)
        self.assertIn("kinds/status-flow/scripts/extract.mjs", kinds)

    def test_nothing_in_the_core_points_to_the_old_status_flow_skill(self):
        old = "skills/" + "status-flow"
        hits = []
        for top, dirs, files in os.walk(CORE):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "worktrees", "workflow-runs")]
            for name in files:
                path = os.path.join(top, name)
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                if re.search(re.escape(old) + r"(?![\w-])", text) or "skills/" + "status_flow" in text:
                    hits.append(os.path.relpath(path, CORE))
        self.assertFalse(os.path.exists(os.path.join(CORE, old)))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
