import json
import os
import shutil
import subprocess
import tempfile
import unittest

from test_status_flow import needs_node, read_json, run, typescript5

CORE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAGRAM = os.path.join(CORE, "skills", "diagram")
KIND = os.path.join(DIAGRAM, "kinds", "call-tree")
EXTRACT = os.path.join(KIND, "scripts", "extract.mjs")
COMPARE = os.path.join(DIAGRAM, "scripts", "compare.mjs")
FIXTURES = os.path.join(CORE, "tests", "fixtures", "diagram", "call-tree")


def extract_run(*args):
    """Run extract.mjs, failing rather than hanging when the call tree loops."""
    try:
        return subprocess.run(["node", EXTRACT, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
    except subprocess.TimeoutExpired:
        raise AssertionError("extract.mjs ran for 60s: the call tree never ended") from None


class FixtureProject(unittest.TestCase):
    """A throwaway git repository holding the three-file fixture, the tiny-format package and TypeScript 5."""

    @classmethod
    def setUpClass(cls):
        needs_node()
        cls.ts = typescript5()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        shutil.copytree(os.path.join(FIXTURES, "project"), self.root, dirs_exist_ok=True)
        run("git", "init", "-q", self.root)
        modules = os.path.join(self.root, "node_modules")
        shutil.copytree(os.path.join(FIXTURES, "packages", "tiny-format"), os.path.join(modules, "tiny-format"))
        os.symlink(self.ts, os.path.join(modules, "typescript"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as f:
            f.write(text)

    def extract(self, function, *args, file="main.ts"):
        return extract_run(os.path.join(self.root, file), "--function", function, *args)

    def graph(self, function, *args, file="main.ts"):
        r = self.extract(function, *args, file=file)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)


def node_ids(graph):
    return {n["id"] for n in graph["nodes"]}


def edges(graph):
    return {(e["from"], e["to"]) for e in graph["edges"]}


class ExtractTest(FixtureProject):
    """extract.mjs follows calls from one function across files and writes a graph file."""

    def test_every_function_reached_across_files_and_no_others(self):
        graph = self.graph("main")
        self.assertEqual(node_ids(graph), {
            "main.ts#main", "orders.ts#placeOrder", "orders.ts#expandTree", "pricing.ts#priceOf",
            "pricing.ts#Discounts.apply", "pricing.ts#roundPrice", "pricing.ts#walkTree", "tiny-format#formatLine"})

    def test_the_graph_matches_the_worked_example(self):
        self.assertEqual(self.graph("main"), read_json(os.path.join(FIXTURES, "main-graph.json")))

    def test_a_call_into_a_package_is_a_leaf_in_the_package_group(self):
        graph = self.graph("placeOrder", file="orders.ts")
        leaf = next(n for n in graph["nodes"] if n["id"] == "tiny-format#formatLine")
        self.assertEqual(leaf["group"], "tiny-format")
        self.assertIn(("orders.ts#placeOrder", "tiny-format#formatLine"), edges(graph))
        self.assertEqual([e for e in graph["edges"] if e["from"] == "tiny-format#formatLine"], [])

    def test_a_package_function_is_not_followed_into_its_own_calls(self):
        modules = os.path.join(self.root, "node_modules", "tiny-format")
        with open(os.path.join(modules, "package.json"), "w") as f:
            json.dump({"name": "tiny-format", "version": "1.0.0", "types": "index.ts"}, f)
        with open(os.path.join(modules, "index.ts"), "w") as f:
            f.write("export function formatLine(text: string): string { return padLine(text, 4); }\n"
                    "export function padLine(text: string, width: number): string { return text.padEnd(width); }\n")
        graph = self.graph("main")
        self.assertIn("tiny-format#formatLine", node_ids(graph))
        self.assertNotIn("tiny-format#padLine", node_ids(graph))

    def test_mutual_recursion_across_files_ends_with_one_edge_each_way(self):
        graph = self.graph("expandTree", file="orders.ts")
        self.assertEqual(edges(graph), {("orders.ts#expandTree", "pricing.ts#walkTree"),
                                        ("pricing.ts#walkTree", "orders.ts#expandTree")})

    def test_a_function_calling_itself_ends_with_a_loop_edge(self):
        self.write("count.ts", "export function countDown(n: number): number {\n"
                               "  return n <= 0 ? 0 : countDown(n - 1);\n}\n")
        graph = self.graph("countDown", file="count.ts")
        self.assertEqual(edges(graph), {("count.ts#countDown", "count.ts#countDown")})

    def test_a_method_entry_is_named_class_dot_method(self):
        graph = self.graph("Discounts.apply", file="pricing.ts")
        self.assertEqual(edges(graph), {("pricing.ts#Discounts.apply", "pricing.ts#roundPrice")})

    def test_an_arrow_function_held_in_a_const_is_followed(self):
        self.write("arrows.ts", 'import { priceOf } from "./pricing";\n'
                                "const half = (n: number): number => n / 2;\n"
                                'export const cheap = (): number => half(priceOf("pen"));\n')
        graph = self.graph("cheap", file="arrows.ts")
        self.assertEqual(edges(graph), {("arrows.ts#cheap", "arrows.ts#half"), ("arrows.ts#cheap", "pricing.ts#priceOf"),
                                        ("pricing.ts#priceOf", "pricing.ts#Discounts.apply"),
                                        ("pricing.ts#Discounts.apply", "pricing.ts#roundPrice")})

    def test_an_unknown_entry_function_is_refused(self):
        r = self.extract("checkout")
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("no function named checkout", r.stderr)

    def test_out_writes_the_graph_file(self):
        out = os.path.join(self.root, "graph.json")
        r = self.extract("main", "--out", out)
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)
        self.assertEqual(read_json(out), read_json(os.path.join(FIXTURES, "main-graph.json")))


class ComparisonTest(FixtureProject):
    """A before and after pair differing by one call compares as one added edge."""

    def test_one_added_call_is_one_extra_edge(self):
        before, after = os.path.join(self.root, "before.json"), os.path.join(self.root, "after.json")
        self.assertEqual(self.extract("main", "--out", before).returncode, 0)
        shutil.copy(os.path.join(FIXTURES, "after", "main.ts"), os.path.join(self.root, "main.ts"))
        r = self.extract("main", "--out", after)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run("node", COMPARE, before, after)
        self.assertEqual((r.returncode, r.stdout), (1, "extra edge main -> expandTree\n"), r.stderr)


class CompilerLookupTest(unittest.TestCase):
    """The call-tree kind gets its compiler from the same ast lookup as status flow."""

    def setUp(self):
        needs_node()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        run("git", "init", "-q", self.root)
        shutil.copytree(os.path.join(FIXTURES, "project"), self.root, dirs_exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def extract(self, *args):
        return extract_run(os.path.join(self.root, "main.ts"), "--function", "main", *args)

    def test_no_compiler_in_the_repository_relays_the_lookup(self):
        r = self.extract()
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("no typescript AST tool found", r.stderr)

    def test_typescript_7_asks_for_a_typescript_5_path(self):
        d = os.path.join(self.root, "node_modules", "typescript")
        os.makedirs(d)
        with open(os.path.join(d, "package.json"), "w") as f:
            json.dump({"name": "typescript", "version": "7.0.1"}, f)
        r = self.extract()
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("TypeScript 7.0.1 has no stable JS API", r.stderr)
        r = self.extract("--typescript", typescript5())
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_the_kind_bundles_no_typescript(self):
        package = read_json(os.path.join(KIND, "package.json"))
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            self.assertNotIn(section, package)


class DocsTest(unittest.TestCase):
    def test_the_diagram_skill_lists_the_kind(self):
        with open(os.path.join(DIAGRAM, "SKILL.md"), encoding="utf-8") as f:
            kinds = f.read().split("## Kinds", 1)[1].split("\n## ", 1)[0]
        self.assertIn("kinds/call-tree/references/call-tree.md", kinds)
        self.assertIn("kinds/call-tree/scripts/extract.mjs", kinds)


if __name__ == "__main__":
    unittest.main()
