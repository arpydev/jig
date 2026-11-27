import { COLOURS, GraphError, loadGraph, runCli } from "./graph.mjs";

const quote = (s) => `"${String(s).replace(/"/g, "#quot;")}"`;

function mermaid(graph) {
  const ids = new Map();
  graph.groups.forEach((g, i) => ids.set(`g:${g.id}`, `g${i}`));
  graph.nodes.forEach((n, i) => ids.set(`n:${n.id}`, `n${i}`));
  const node = (n) => `${ids.get(`n:${n.id}`)}[${quote(n.label)}]`;
  const lines = ["```mermaid", "flowchart LR"];
  for (const g of graph.groups) {
    lines.push(`  subgraph ${ids.get(`g:${g.id}`)}[${quote(g.label)}]`);
    for (const n of graph.nodes.filter((n) => n.group === g.id)) lines.push(`    ${node(n)}`);
    lines.push("  end");
  }
  for (const n of graph.nodes.filter((n) => !n.group)) lines.push(`  ${node(n)}`);
  for (const e of graph.edges) {
    const arrow = e.mark === "removed" ? "-.->" : "-->";
    const label = e.label ? `|${quote(e.label)}|` : "";
    lines.push(`  ${ids.get(`n:${e.from}`)} ${arrow}${label} ${ids.get(`n:${e.to}`)}`);
  }
  for (const [mark, c] of Object.entries(COLOURS)) {
    const dash = mark === "removed" ? ",stroke-dasharray:6 4" : "";
    lines.push(`  classDef ${mark} fill:${c.fill},stroke:${c.stroke}${dash}`);
  }
  for (const g of graph.groups) lines.push(`  class ${ids.get(`g:${g.id}`)} ${g.mark}`);
  for (const n of graph.nodes) lines.push(`  class ${ids.get(`n:${n.id}`)} ${n.mark}`);
  graph.edges.forEach((e, i) => lines.push(`  linkStyle ${i} stroke:${COLOURS[e.mark].stroke}`));
  lines.push("```");
  return lines.join("\n");
}

runCli(async () => {
  const [input] = process.argv.slice(2);
  if (!input) throw new GraphError("usage: mermaid.mjs <graph.json>");
  console.log(mermaid(loadGraph(input)));
});
