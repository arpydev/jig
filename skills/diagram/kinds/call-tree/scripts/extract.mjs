import { writeFileSync } from "node:fs";
import path from "node:path";
import { checkGraph, GraphError } from "../../../scripts/graph.mjs";
import { runKind, typescriptFor } from "../../../scripts/typescript.mjs";

const USAGE = "usage: extract.mjs <file.ts> --function <name or Class.method> [--typescript <path>] [--out <graph.json>]";

function parseArgs(argv) {
  const args = [...argv];
  const flag = (name) => {
    const i = args.indexOf(name);
    return i >= 0 ? args.splice(i, 2)[1] : undefined;
  };
  const options = { function: flag("--function"), typescript: flag("--typescript"), out: flag("--out") };
  if (args.length !== 1 || !options.function) throw new GraphError(USAGE);
  return { file: path.resolve(args[0]), ...options };
}

function createProgram(ts, file) {
  const config = ts.findConfigFile(path.dirname(file), ts.sys.fileExists);
  if (!config) {
    const options = { allowJs: true, noEmit: true, target: ts.ScriptTarget.Latest, moduleResolution: ts.ModuleResolutionKind.Node10 };
    return { program: ts.createProgram([file], options), root: path.dirname(file) };
  }
  const { config: json } = ts.readConfigFile(config, ts.sys.readFile);
  const { options } = ts.parseJsonConfigFileContent(json, ts.sys, path.dirname(config));
  return { program: ts.createProgram([file], { ...options, noEmit: true }), root: path.dirname(config) };
}

function packageOf(fileName) {
  const parts = fileName.split(/[\\/]/);
  const i = parts.lastIndexOf("node_modules");
  return parts[i + 1].startsWith("@") ? `${parts[i + 1]}/${parts[i + 2]}` : parts[i + 1];
}

function extract(ts, program, root, entryFile, entryName) {
  const checker = program.getTypeChecker();
  const groups = new Map();
  const nodes = new Map();
  const edges = new Map();

  const bodyOf = (decl) => {
    if (ts.isVariableDeclaration(decl) && decl.initializer && ts.isFunctionLike(decl.initializer)) return decl.initializer;
    if ((ts.isFunctionDeclaration(decl) || ts.isMethodDeclaration(decl) || ts.isFunctionExpression(decl) || ts.isArrowFunction(decl)) && decl.body) {
      return decl;
    }
    return undefined;
  };
  const nameOf = (decl) => {
    const own = decl.name.getText();
    const owner = decl.parent;
    return ts.isMethodDeclaration(decl) && owner.name ? `${owner.name.text}.${own}` : own;
  };
  const isPackage = (sf) => program.isSourceFileFromExternalLibrary(sf) || /[\\/]node_modules[\\/]/.test(sf.fileName);
  const isFunction = (decl) =>
    ts.isFunctionDeclaration(decl) || ts.isMethodDeclaration(decl) || ts.isMethodSignature(decl) || Boolean(bodyOf(decl));

  const addNode = (decl) => {
    const sf = decl.getSourceFile();
    const name = nameOf(decl);
    const leaf = isPackage(sf);
    const group = leaf ? packageOf(sf.fileName) : path.relative(root, sf.fileName);
    const id = `${group}#${name}`;
    if (!groups.has(group)) groups.set(group, { id: group, label: leaf ? `${group} (package)` : group });
    if (!nodes.has(id)) nodes.set(id, { node: { id, label: name, group }, decl, leaf });
    return id;
  };

  const calleeOf = (call) => {
    let symbol = checker.getSymbolAtLocation(call.expression);
    if (symbol && symbol.flags & ts.SymbolFlags.Alias) symbol = checker.getAliasedSymbol(symbol);
    const decl = symbol?.declarations?.[0];
    if (!decl || !isFunction(decl)) return undefined;
    const sf = decl.getSourceFile();
    if (program.isSourceFileDefaultLibrary(sf)) return undefined;
    if (!isPackage(sf) && !bodyOf(decl)) return undefined;
    return decl;
  };

  const callsIn = (fn) => {
    const found = [];
    const walk = (node) => {
      if (ts.isCallExpression(node)) {
        const decl = calleeOf(node);
        if (decl) found.push(decl);
      }
      ts.forEachChild(node, walk);
    };
    ts.forEachChild(bodyOf(fn), walk);
    return found;
  };

  const entry = findEntry(ts, program.getSourceFile(entryFile), entryName, bodyOf, nameOf);
  const queue = [addNode(entry)];
  const queued = new Set(queue);
  for (let i = 0; i < queue.length; i++) {
    const from = nodes.get(queue[i]);
    if (from.leaf) continue;
    for (const decl of callsIn(from.decl)) {
      const to = addNode(decl);
      if (!queued.has(to)) queue.push(to);
      queued.add(to);
      edges.set(`${from.node.id} -> ${to}`, { from: from.node.id, to });
    }
  }

  return {
    title: `Calls from ${entryName} in ${path.basename(entryFile)}`,
    groups: [...groups.values()],
    nodes: [...nodes.values()].map((n) => n.node),
    edges: [...edges.values()],
  };
}

function findEntry(ts, sf, name, bodyOf, nameOf) {
  let found;
  const visit = (node) => {
    if (found) return;
    if ((ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isVariableDeclaration(node)) && node.name && bodyOf(node)) {
      if (nameOf(node) === name) found = node;
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  if (!found) throw new GraphError(`${sf.fileName}: no function named ${name}`);
  return found;
}

runKind(async () => {
  const options = parseArgs(process.argv.slice(2));
  const ts = typescriptFor(options.file, options.typescript);
  const { program, root } = createProgram(ts, options.file);
  const graph = extract(ts, program, root, options.file, options.function);
  checkGraph(graph, options.file);
  const text = `${JSON.stringify(graph, null, 2)}\n`;
  if (options.out) writeFileSync(options.out, text);
  else process.stdout.write(text);
});
