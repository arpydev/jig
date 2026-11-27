import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { runCli } from "./graph.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const AST_TOOL = path.join(HERE, "..", "..", "ast", "scripts", "ast_tool.py");

export class LookupError extends Error {}

function lookUpTypescript(file) {
  try {
    return execFileSync("python3", [AST_TOOL, "find", "typescript", "--repo", path.dirname(file)], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
  } catch (e) {
    throw new LookupError(`the ast lookup found no single TypeScript compiler: ${String(e.stderr).trim()}`);
  }
}

function loadTypescript(tsPath) {
  const manifest = path.join(tsPath, "package.json");
  if (!existsSync(manifest)) {
    throw new LookupError(`${tsPath} is not a TypeScript package; pass a TypeScript 5.x folder with --typescript <path>`);
  }
  const { name, version } = JSON.parse(readFileSync(manifest, "utf8"));
  if (name !== "typescript") {
    throw new LookupError(`${tsPath} is ${name}, not typescript; pass a TypeScript 5.x folder with --typescript <path>`);
  }
  if (Number(version.split(".")[0]) >= 7) {
    throw new LookupError(
      `TypeScript ${version} has no stable JS API; ask the developer for a TypeScript 5.x folder ` +
        "(for example `pnpm add typescript@5 --dir <temp folder>`) and pass it with --typescript <path>",
    );
  }
  return createRequire(import.meta.url)(tsPath);
}

export function typescriptFor(file, typescriptPath) {
  return loadTypescript(typescriptPath ? path.resolve(typescriptPath) : lookUpTypescript(file));
}

export function runKind(main) {
  runCli(async () => {
    try {
      await main();
    } catch (e) {
      if (!(e instanceof LookupError)) throw e;
      console.error(e.message);
      process.exit(3);
    }
  });
}
