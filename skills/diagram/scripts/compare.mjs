import { GraphError, describe, edgeKey, loadGraph, runCli } from "./graph.mjs";

const SECTIONS = [
  ["group", "groups", (g) => g.id, ["label", "mark"]],
  ["node", "nodes", (n) => n.id, ["label", "group", "mark"]],
  ["edge", "edges", edgeKey, ["label", "mark"]],
];

function compare(plan, proof) {
  const lines = [];
  for (const [kind, key, idOf, fields] of SECTIONS) {
    const planned = new Map(plan[key].map((item) => [idOf(item), item]));
    const proven = new Map(proof[key].map((item) => [idOf(item), item]));
    for (const [id, item] of planned) {
      if (!proven.has(id)) lines.push(`missing ${describe(plan, kind, item)}`);
    }
    for (const [id, item] of proven) {
      if (!planned.has(id)) {
        lines.push(`extra ${describe(proof, kind, item)}`);
        continue;
      }
      const before = planned.get(id);
      const changes = fields
        .filter((f) => (before[f] ?? "") !== (item[f] ?? ""))
        .map((f) => `${f} ${before[f] ?? "(none)"}, now ${item[f] ?? "(none)"}`);
      const name = describe(plan, kind, kind === "edge" ? { ...before, label: "" } : before);
      if (changes.length) lines.push(`changed ${name}: ${changes.join("; ")}`);
    }
  }
  return lines;
}

runCli(async () => {
  const [planPath, proofPath] = process.argv.slice(2);
  if (!planPath || !proofPath) throw new GraphError("usage: compare.mjs <plan.json> <proof.json>");
  const lines = compare(loadGraph(planPath), loadGraph(proofPath));
  for (const line of lines) console.log(line);
  process.exitCode = lines.length ? 1 : 0;
});
