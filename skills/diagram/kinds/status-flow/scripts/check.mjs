import { readFileSync } from "node:fs";
import { GraphError, loadGraph, runCli } from "../../../scripts/graph.mjs";

function loadRules(path, graph) {
  let rules;
  try {
    rules = JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    throw new GraphError(`${path}: ${e.message}`);
  }
  const fail = (msg) => { throw new GraphError(`${path}: ${msg}`); };
  const states = new Set(graph.nodes.map((n) => n.id));
  const state = (id, where) => {
    if (!states.has(id)) fail(`${where} names unknown state ${id}`);
  };
  if (!Array.isArray(rules.start) || !rules.start.length) fail("start must list at least one state");
  rules.start.forEach((s) => state(s, "start"));
  const flags = rules.flags ?? {};
  for (const [flag, setBy] of Object.entries(flags)) {
    if (!Array.isArray(setBy)) fail(`flag ${flag} must list the states that set it`);
    setBy.forEach((s) => state(s, `flag ${flag}`));
  }
  if (!Array.isArray(rules.rules) || !rules.rules.length) fail("rules must list at least one rule");
  const names = new Set();
  for (const rule of rules.rules) {
    if (!rule.name) fail("a rule has no name");
    if (names.has(rule.name)) fail(`rule ${rule.name} appears twice`);
    names.add(rule.name);
    const where = `rule ${rule.name}`;
    if (("never" in rule) === ("reach" in rule)) fail(`${where} needs exactly one of never or reach`);
    state(rule.never ?? rule.reach, where);
    if (rule.unless !== undefined) {
      if (!("never" in rule)) fail(`${where}: unless only goes with never`);
      for (const flag of rule.unless) if (!Object.hasOwn(flags, flag)) fail(`${where} names unknown flag ${flag}`);
    }
  }
  return { start: rules.start, flags, rules: rules.rules };
}

function explore(graph, rules) {
  const next = new Map(graph.nodes.map((n) => [n.id, []]));
  for (const e of graph.edges) if (e.mark !== "removed") next.get(e.from).push(e.to);
  const flagsAt = (node, held) => {
    const flags = new Set(held);
    for (const [flag, setBy] of Object.entries(rules.flags)) if (setBy.includes(node)) flags.add(flag);
    return [...flags].sort();
  };
  const key = (s) => `${s.node}|${s.flags.join(",")}`;
  const seen = new Map();
  const queue = [];
  for (const node of rules.start) {
    const s = { node, flags: flagsAt(node, []), parent: null };
    if (!seen.has(key(s))) { seen.set(key(s), s); queue.push(s); }
  }
  for (let i = 0; i < queue.length; i++) {
    const at = queue[i];
    for (const node of next.get(at.node)) {
      const s = { node, flags: flagsAt(node, at.flags), parent: at };
      if (!seen.has(key(s))) { seen.set(key(s), s); queue.push(s); }
    }
  }
  return queue;
}

function pathTo(graph, s) {
  const label = (id) => graph.nodes.find((n) => n.id === id).label;
  const steps = [];
  for (let at = s; at; at = at.parent) steps.unshift(label(at.node));
  return steps.join(" -> ");
}

runCli(async () => {
  const [graphPath, rulesPath, ...rest] = process.argv.slice(2);
  if (!graphPath || !rulesPath || rest.length) throw new GraphError("usage: check.mjs <graph.json> <rules.json>");
  const graph = loadGraph(graphPath);
  const rules = loadRules(rulesPath, graph);
  const visited = explore(graph, rules);
  const broken = [];
  for (const rule of rules.rules) {
    const head = `broken ${rule.name}${rule.says ? ` (${rule.says})` : ""}`;
    if ("reach" in rule) {
      if (!visited.some((s) => s.node === rule.reach)) {
        broken.push(`${head}: ${graph.nodes.find((n) => n.id === rule.reach).label} is never reached`);
      }
      continue;
    }
    const excused = (s) => rule.unless?.length > 0 && rule.unless.every((flag) => s.flags.includes(flag));
    const breach = visited.find((s) => s.node === rule.never && !excused(s));
    if (breach) broken.push(`${head}: ${pathTo(graph, breach)}`);
  }
  if (broken.length) {
    console.log(broken.join("\n"));
    process.exit(1);
  }
  console.log(`${rules.rules.length} rules hold`);
});
