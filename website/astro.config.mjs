import { defineConfig } from "astro/config";
import { fileURLToPath } from "node:url";

// The site reads Jig's own files, one folder up from this config.
const repoRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig({
  output: "static",
  trailingSlash: "always",
  vite: { define: { __REPO_ROOT__: JSON.stringify(repoRoot) } },
});
