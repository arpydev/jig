import { readFileSync } from "node:fs";

export const COLOURS = {
  added: { stroke: "#2e7d32", fill: "#e8f5e9" },
  removed: { stroke: "#c62828", fill: "#ffebee" },
  unchanged: { stroke: "#757575", fill: "#f5f5f5" },
  mismatch: { stroke: "#ef8f00", fill: "#fff3e0" },
};

export class GraphError extends Error {}

export function loadGraph(path) {
  let graph;
  try {
    graph = JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    throw new GraphError(`${path}: ${e.message}`);
  }
  return checkGraph(graph, path);
}

export function checkGraph(graph, name = "graph") {
  const fail = (msg) => { throw new GraphError(`${name}: ${msg}`); };
  const groups = graph.groups ?? [];
  const nodes = graph.nodes ?? [];
  const edges = graph.edges ?? [];
  const groupIds = new Set();
  for (const g of groups) {
    if (!g.id) fail("a group has no id");
    if (groupIds.has(g.id)) fail(`group ${g.id} appears twice`);
    groupIds.add(g.id);
  }
  const nodeIds = new Set();
  for (const n of nodes) {
    if (!n.id) fail("a node has no id");
    if (nodeIds.has(n.id)) fail(`node ${n.id} appears twice`);
    if (n.group && !groupIds.has(n.group)) fail(`node ${n.id} is in unknown group ${n.group}`);
    nodeIds.add(n.id);
  }
  const edgeKeys = new Set();
  for (const e of edges) {
    if (!nodeIds.has(e.from) || !nodeIds.has(e.to)) fail(`edge ${e.from} -> ${e.to} names an unknown node`);
    if (edgeKeys.has(edgeKey(e))) fail(`edge ${e.from} -> ${e.to} appears twice`);
    edgeKeys.add(edgeKey(e));
  }
  for (const item of [...groups, ...nodes, ...edges]) {
    if (item.mark !== undefined && !Object.hasOwn(COLOURS, item.mark)) fail(`unknown mark ${item.mark}`);
  }
  return {
    title: graph.title ?? "",
    groups: groups.map((g) => ({ label: g.id, ...g, mark: g.mark ?? "unchanged" })),
    nodes: nodes.map((n) => ({ label: n.id, ...n, mark: n.mark ?? "unchanged" })),
    edges: edges.map((e) => ({ label: "", ...e, mark: e.mark ?? "unchanged" })),
  };
}

export function edgeKey(edge) {
  return `${edge.from} -> ${edge.to}`;
}

export const SECTIONS = [
  ["group", "groups", (g) => g.id, ["label", "mark"]],
  ["node", "nodes", (n) => n.id, ["label", "group", "mark"]],
  ["edge", "edges", edgeKey, ["label", "mark"]],
];

export function pair(left, right, key, idOf) {
  const lefts = new Map(left[key].map((item) => [idOf(item), item]));
  const rights = new Map(right[key].map((item) => [idOf(item), item]));
  const pairs = [...rights].map(([id, item]) => [id, lefts.get(id), item]);
  for (const [id, item] of lefts) if (!rights.has(id)) pairs.push([id, item, undefined]);
  return pairs;
}

export function describe(graph, kind, item) {
  if (kind === "edge") {
    const name = (id) => graph.nodes.find((n) => n.id === id).label;
    const label = item.label ? ` (${item.label})` : "";
    return `edge ${name(item.from)} -> ${name(item.to)}${label}`;
  }
  return `${kind} ${item.label}`;
}

export function differences(graph) {
  const items = [
    ...graph.groups.map((g) => ["group", g]),
    ...graph.nodes.map((n) => ["node", n]),
    ...graph.edges.map((e) => ["edge", e]),
  ];
  return items
    .filter(([, item]) => item.mark !== "unchanged")
    .map(([kind, item]) => ({ mark: item.mark, text: `${item.mark} ${describe(graph, kind, item)}` }));
}

export function runCli(main) {
  main().catch((e) => {
    console.error(e instanceof GraphError ? e.message : e.stack);
    process.exit(2);
  });
}
