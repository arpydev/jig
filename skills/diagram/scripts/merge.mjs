import { writeFileSync } from "node:fs";
import { GraphError, SECTIONS, checkGraph, loadGraph, pair, runCli } from "./graph.mjs";

function merge(before, after) {
  const merged = { title: after.title || before.title };
  for (const [, key, idOf] of SECTIONS) {
    merged[key] = pair(before, after, key, idOf).map(([, old, now]) => ({
      ...(now ?? old),
      mark: !old ? "added" : !now ? "removed" : "unchanged",
    }));
  }
  return checkGraph(merged, "merged graph");
}

runCli(async () => {
  const [beforePath, afterPath, outPath] = process.argv.slice(2);
  if (!outPath) throw new GraphError("usage: merge.mjs <before.json> <after.json> <out.json>");
  const merged = merge(loadGraph(beforePath), loadGraph(afterPath));
  writeFileSync(outPath, JSON.stringify(merged, null, 2) + "\n");
});
