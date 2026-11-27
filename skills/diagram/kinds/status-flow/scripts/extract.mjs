import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { checkGraph, GraphError } from "../../../scripts/graph.mjs";
import { runKind, typescriptFor } from "../../../scripts/typescript.mjs";

const USAGE = "usage: extract.mjs <file.ts> --states <enum or union type> [--field status] [--typescript <path>] [--out <graph.json>]";

function parseArgs(argv) {
  const args = [...argv];
  const flag = (name, fallback) => {
    const i = args.indexOf(name);
    return i >= 0 ? args.splice(i, 2)[1] : fallback;
  };
  const options = {
    states: flag("--states"),
    field: flag("--field", "status"),
    typescript: flag("--typescript"),
    out: flag("--out"),
  };
  if (args.length !== 1 || !options.states) throw new GraphError(USAGE);
  return { file: path.resolve(args[0]), ...options };
}

function findStates(ts, sf, typeName) {
  for (const statement of sf.statements) {
    if (ts.isEnumDeclaration(statement) && statement.name.text === typeName) {
      const names = statement.members.map((m) => m.name.getText(sf));
      return { names, of: (e) => (ts.isPropertyAccessExpression(e) && e.expression.getText(sf) === typeName ? e.name.text : undefined) };
    }
    if (ts.isTypeAliasDeclaration(statement) && statement.name.text === typeName && ts.isUnionTypeNode(statement.type)) {
      const names = statement.type.types
        .filter((t) => ts.isLiteralTypeNode(t) && ts.isStringLiteral(t.literal))
        .map((t) => t.literal.text);
      return { names, of: (e) => (ts.isStringLiteralLike(e) ? e.text : undefined) };
    }
  }
  throw new GraphError(`${sf.fileName}: no enum or string union type named ${typeName}`);
}

function extract(ts, sf, typeName, field) {
  const states = findStates(ts, sf, typeName);
  const strip = (e) => {
    while (ts.isParenthesizedExpression(e) || ts.isAsExpression(e) || ts.isNonNullExpression(e)) e = e.expression;
    return e;
  };
  const stateOf = (e) => {
    const name = states.of(strip(e));
    return states.names.includes(name) ? name : undefined;
  };
  const isField = (e) => {
    e = strip(e);
    return (ts.isPropertyAccessExpression(e) && e.name.text === field) || (ts.isIdentifier(e) && e.text === field);
  };
  const edges = new Map();
  const addEdge = (from, to, label) => {
    if (from === to) return;
    const key = `${from} -> ${to}`;
    const edge = edges.get(key) ?? { from, to, labels: [] };
    if (label && !edge.labels.includes(label)) edge.labels.push(label);
    edges.set(key, edge);
  };
  const warnings = [];

  const readTable = (object) => {
    const rows = object.properties.map((p) => {
      if (!ts.isPropertyAssignment(p)) return undefined;
      const key = ts.isComputedPropertyName(p.name) ? stateOf(p.name.expression) : states.names.find((n) => n === p.name.text);
      return key && { from: key, value: strip(p.initializer) };
    });
    if (!rows.length || rows.some((r) => !r)) return false;
    for (const { from, value } of rows) {
      if (ts.isArrayLiteralExpression(value)) {
        for (const e of value.elements) if (stateOf(e)) addEdge(from, stateOf(e));
      } else if (ts.isObjectLiteralExpression(value)) {
        for (const p of value.properties) {
          if (ts.isPropertyAssignment(p) && stateOf(p.initializer)) addEdge(from, stateOf(p.initializer), p.name.getText(sf));
        }
      }
    }
    return true;
  };

  const S = ts.SyntaxKind;
  const EQUAL = [S.EqualsEqualsEqualsToken, S.EqualsEqualsToken];
  const NOT_EQUAL = [S.ExclamationEqualsEqualsToken, S.ExclamationEqualsToken];
  const comparison = (node) => {
    if (ts.isBinaryExpression(node) && [...EQUAL, ...NOT_EQUAL].includes(node.operatorToken.kind)) {
      const state = (isField(node.left) && stateOf(node.right)) || (isField(node.right) && stateOf(node.left));
      return state && { states: [state], equal: EQUAL.includes(node.operatorToken.kind) };
    }
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression) && node.expression.name.text === "includes") {
      const list = strip(node.expression.expression);
      if (ts.isArrayLiteralExpression(list) && node.arguments.length === 1 && isField(node.arguments[0])) {
        return { states: list.elements.map(stateOf).filter(Boolean), equal: true };
      }
    }
    return undefined;
  };
  const branchStates = (e, equal = true, out = { then: new Set(), otherwise: new Set() }) => {
    e = strip(e);
    if (ts.isPrefixUnaryExpression(e) && e.operator === S.ExclamationToken) return branchStates(e.operand, !equal, out);
    if (ts.isBinaryExpression(e) && [S.BarBarToken, S.AmpersandAmpersandToken].includes(e.operatorToken.kind)) {
      branchStates(e.left, equal, out);
      return branchStates(e.right, equal, out);
    }
    const found = comparison(e);
    if (found) for (const st of found.states) out[found.equal === equal ? "then" : "otherwise"].add(st);
    return out;
  };
  const exits = (statement) => {
    const last = ts.isBlock(statement) ? statement.statements.at(-1) : statement;
    return Boolean(last) && (ts.isThrowStatement(last) || ts.isReturnStatement(last));
  };

  const readFunction = (name, body) => {
    const loose = new Set();
    const unpaired = new Set();
    const assign = (active, t) => {
      if (active.size) active.forEach((f) => addEdge(f, t, name));
      else unpaired.add(t);
    };
    const readBlock = (statements, active) => {
      for (const statement of statements) {
        if (ts.isIfStatement(statement)) {
          const { then, otherwise } = branchStates(statement.expression);
          walk(statement.thenStatement, then.size ? then : active);
          if (statement.elseStatement) walk(statement.elseStatement, otherwise.size ? otherwise : active);
          if (exits(statement.thenStatement) && otherwise.size) active = otherwise;
          continue;
        }
        walk(statement, active);
      }
    };
    const walk = (node, active) => {
      if (node !== body && ts.isFunctionLike(node)) return;
      if (ts.isBlock(node) || ts.isSourceFile(node)) return readBlock(node.statements, active);
      if (ts.isIfStatement(node)) return readBlock([node], active);
      if (ts.isSwitchStatement(node) && isField(node.expression)) {
        let falling = [];
        for (const clause of node.caseBlock.clauses) {
          if (ts.isCaseClause(clause) && stateOf(clause.expression)) falling.push(stateOf(clause.expression));
          if (!clause.statements.length) continue;
          readBlock(clause.statements, new Set(falling));
          falling = [];
        }
        return;
      }
      comparison(node)?.states.forEach((st) => loose.add(st));
      collectTo(node, (t) => assign(active, t), true);
      ts.forEachChild(node, (child) => walk(child, active));
    };
    walk(body, new Set());
    // why: a check outside an if condition (a ternary, a loop) can't be tied to one branch, so it pairs with every unchecked assignment as before.
    for (const f of loose) for (const t of unpaired) addEdge(f, t, name);
    if (unpaired.size && !loose.size) {
      warnings.push(`${name} sets ${field} to ${[...unpaired].join(", ")} without checking the ${field} first; not drawn`);
    }
  };

  function collectTo(node, add, shallow = false) {
    const visit = (n) => {
      if (ts.isFunctionLike(n)) return;
      if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken && isField(n.left) && stateOf(n.right)) add(stateOf(n.right));
      if (ts.isPropertyAssignment(n) && n.name.getText(sf) === field && stateOf(n.initializer)) add(stateOf(n.initializer));
      if (!shallow) ts.forEachChild(n, visit);
    };
    visit(node);
  }

  const functionName = (node) => {
    if (node.name && (ts.isIdentifier(node.name) || ts.isPrivateIdentifier(node.name))) return node.name.text;
    const parent = node.parent;
    if (parent && (ts.isVariableDeclaration(parent) || ts.isPropertyAssignment(parent) || ts.isPropertyDeclaration(parent))) {
      return parent.name.getText(sf);
    }
    return undefined;
  };

  const visit = (node) => {
    if (ts.isObjectLiteralExpression(node) && readTable(node)) return;
    if (ts.isFunctionLike(node) && node.body) {
      const name = functionName(node);
      if (name) readFunction(name, node.body);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);

  const graph = {
    title: `${typeName} in ${path.basename(sf.fileName)}`,
    nodes: states.names.map((n) => ({ id: n, label: n })),
    edges: [...edges.values()].map(({ from, to, labels }) => ({ from, to, ...(labels.length ? { label: labels.join(", ") } : {}) })),
  };
  return { graph, warnings };
}

runKind(async () => {
  const options = parseArgs(process.argv.slice(2));
  const ts = typescriptFor(options.file, options.typescript);
  const sf = ts.createSourceFile(options.file, readFileSync(options.file, "utf8"), ts.ScriptTarget.Latest, true);
  const { graph, warnings } = extract(ts, sf, options.states, options.field);
  checkGraph(graph, options.file);
  for (const w of warnings) console.error(`warning: ${w}`);
  const text = `${JSON.stringify(graph, null, 2)}\n`;
  if (options.out) writeFileSync(options.out, text);
  else process.stdout.write(text);
});
