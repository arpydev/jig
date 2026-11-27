import { GraphError, SECTIONS, describe, loadGraph, pair, runCli } from "./graph.mjs";

function compare(plan, proof) {
  const lines = [];
  for (const [kind, key, idOf, fields] of SECTIONS) {
    const pairs = pair(plan, proof, key, idOf);
    for (const [, before, item] of pairs) {
      if (!item) lines.push(`missing ${describe(plan, kind, before)}`);
    }
    for (const [, before, item] of pairs) {
      if (!item) continue;
      if (!before) {
        lines.push(`extra ${describe(proof, kind, item)}`);
        continue;
      }
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
