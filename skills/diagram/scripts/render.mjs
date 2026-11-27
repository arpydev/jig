import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { COLOURS, GraphError, differences, loadGraph, runCli } from "./graph.mjs";

const FONT = 13;
const CHAR = 7.5;
const PAD = 20;

function loadElk() {
  try {
    const ELK = createRequire(import.meta.url)("elkjs/lib/elk.bundled.js");
    return new ELK();
  } catch {
    throw new GraphError(`elkjs is not installed: run pnpm install --dir ${new URL("..", import.meta.url).pathname}`);
  }
}

const escape = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const textWidth = (s) => Math.ceil(s.length * CHAR);

function elkGraph(graph) {
  const box = (n) => ({ id: `n:${n.id}`, width: textWidth(n.label) + 2 * PAD, height: 36 });
  const children = graph.groups.map((g) => ({
    id: `g:${g.id}`,
    layoutOptions: { "elk.padding": `[top=${FONT + 22},left=14,bottom=14,right=14]` },
    children: graph.nodes.filter((n) => n.group === g.id).map(box),
  }));
  children.push(...graph.nodes.filter((n) => !n.group).map(box));
  return {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.layered.spacing.nodeNodeBetweenLayers": "60",
      "elk.spacing.edgeLabel": "4",
      "elk.json.shapeCoords": "ROOT",
      "elk.json.edgeCoords": "ROOT",
    },
    children,
    edges: graph.edges.map((e, i) => ({
      id: `e:${i}`,
      sources: [`n:${e.from}`],
      targets: [`n:${e.to}`],
      labels: e.label ? [{ text: e.label, width: textWidth(e.label), height: FONT + 4 }] : [],
    })),
  };
}

function flatten(laid) {
  const shapes = {};
  const edges = {};
  const walk = (n) => {
    shapes[n.id] = n;
    for (const e of n.edges ?? []) edges[e.id] = e;
    for (const c of n.children ?? []) walk(c);
  };
  walk(laid);
  return { shapes, edges };
}

function drawSvg(graph, laid) {
  const { shapes, edges } = flatten(laid);
  const out = [];
  for (const mark of Object.keys(COLOURS)) {
    out.push(`<marker id="arrow-${mark}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${COLOURS[mark].stroke}"/></marker>`);
  }
  out.unshift("<defs>");
  out.push("</defs>");
  const dash = (mark) => (mark === "removed" ? ' stroke-dasharray="6 4"' : "");
  for (const g of graph.groups) {
    const s = shapes[`g:${g.id}`];
    const c = COLOURS[g.mark];
    out.push(`<g class="group" data-id="${escape(g.id)}" data-mark="${g.mark}"><rect x="${s.x}" y="${s.y}" width="${s.width}" height="${s.height}" rx="8" fill="none" stroke="${c.stroke}"${dash(g.mark)}/><text x="${s.x + 10}" y="${s.y + FONT + 8}" fill="${c.stroke}" font-weight="bold">${escape(g.label)}</text></g>`);
  }
  graph.edges.forEach((e, i) => {
    const laidEdge = edges[`e:${i}`];
    const c = COLOURS[e.mark];
    const points = laidEdge.sections.flatMap((s) => [s.startPoint, ...(s.bendPoints ?? []), s.endPoint]);
    const d = points.map((p, j) => `${j ? "L" : "M"}${p.x},${p.y}`).join(" ");
    const parts = [`<path d="${d}" fill="none" stroke="${c.stroke}" stroke-width="1.5"${dash(e.mark)} marker-end="url(#arrow-${e.mark})"/>`];
    for (const l of laidEdge.labels ?? []) {
      parts.push(`<text x="${l.x}" y="${l.y + FONT}" fill="${c.stroke}">${escape(e.label)}</text>`);
    }
    out.push(`<g class="edge" data-from="${escape(e.from)}" data-to="${escape(e.to)}" data-mark="${e.mark}">${parts.join("")}</g>`);
  });
  for (const n of graph.nodes) {
    const s = shapes[`n:${n.id}`];
    const c = COLOURS[n.mark];
    out.push(`<g class="node" data-id="${escape(n.id)}" data-mark="${n.mark}"><rect x="${s.x}" y="${s.y}" width="${s.width}" height="${s.height}" rx="6" fill="${c.fill}" stroke="${c.stroke}" stroke-width="1.5"${dash(n.mark)}/><text x="${s.x + s.width / 2}" y="${s.y + s.height / 2 + FONT / 2 - 1}" text-anchor="middle" fill="#212121">${escape(n.label)}</text></g>`);
  }
  const w = Math.ceil(laid.width) + 2;
  const h = Math.ceil(laid.height) + 2;
  return `<svg width="${w}" height="${h}" viewBox="-1 -1 ${w} ${h}" font-family="sans-serif" font-size="${FONT}">${out.join("\n")}</svg>`;
}

function drawList(graph) {
  const items = differences(graph);
  if (!items.length) return "<p>No differences.</p>";
  const li = items.map((d) => `<li data-mark="${d.mark}" style="color:${COLOURS[d.mark].stroke}">${escape(d.text)}</li>`);
  return `<ul class="differences">\n${li.join("\n")}\n</ul>`;
}

function page(graph, svg) {
  const title = escape(graph.title || "Diagram");
  return `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>${title}</title></head>
<body style="font-family:sans-serif">
<h1>${title}</h1>
${svg}
<h2>Differences</h2>
${drawList(graph)}
</body>
</html>
`;
}

runCli(async () => {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) throw new GraphError("usage: render.mjs <graph.json> <out.html>");
  const graph = loadGraph(input);
  const laid = await loadElk().layout(elkGraph(graph));
  writeFileSync(output, page(graph, drawSvg(graph, laid)));
});
