// Reads Jig's own files at build time, so the site can't drift from the repository.
import fs from "node:fs";
import path from "node:path";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import remarkRehype from "remark-rehype";
import rehypeSlug from "rehype-slug";
import rehypeStringify from "rehype-stringify";
import { visit } from "unist-util-visit";
import { parse as parseYaml } from "yaml";
import { GROUPS } from "./groups";

export const REPO_URL = "https://github.com/arpydev/jig";
declare const __REPO_ROOT__: string;
const ROOT = __REPO_ROOT__;

// Repository files that have their own page on the site.
const PAGES: Record<string, string> = {
  "README.md": "/",
  "GLOSSARY.md": "/glossary/",
  "docs/guide.md": "/guide/",
  "docs/decisions.md": "/decisions/",
};

function siteUrlFor(repoPath: string): string {
  const skill = repoPath.match(/^skills\/([^/]+)\/(SKILL\.md)?$/);
  if (skill) return `/skills/${skill[1]}/`;
  return PAGES[repoPath] ?? `${REPO_URL}/blob/main/${repoPath}`;
}

// Rewrites links that are relative to the source file into site or GitHub links.
function rewriteLinks(source: string) {
  return (tree: any) => {
    visit(tree, ["link", "definition"], (node: any) => {
      const url: string = node.url;
      if (!url || /^[a-z]+:/i.test(url) || url.startsWith("#") || url.startsWith("/")) return;
      const [target, hash] = url.split("#");
      const repoPath = path.posix.normalize(path.posix.join(path.posix.dirname(source), target));
      node.url = siteUrlFor(repoPath) + (hash ? `#${hash}` : "");
    });
  };
}

export type Heading = { id: string; text: string };
export type Rendered = { title: string; html: string; headings: Heading[] };

export function renderFile(source: string): Rendered {
  const text = fs.readFileSync(path.join(ROOT, source), "utf8");
  return renderMarkdown(text, source);
}

export function renderMarkdown(text: string, source: string): Rendered {
  let title = "";
  const headings: Heading[] = [];
  const html = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(() => rewriteLinks(source))
    .use(() => (tree: any) => {
      // The page supplies its own title, so the first h1 is lifted out.
      const i = tree.children.findIndex((n: any) => n.type === "heading" && n.depth === 1);
      if (i >= 0) {
        title = textOf(tree.children[i]);
        tree.children.splice(i, 1);
      }
    })
    .use(remarkRehype)
    .use(rehypeSlug)
    .use(() => (tree: any) => {
      visit(tree, "element", (node: any) => {
        if (node.tagName === "h2") headings.push({ id: node.properties.id, text: textOf(node) });
      });
    })
    .use(rehypeStringify)
    .processSync(text)
    .toString();
  return { title, html, headings };
}

function textOf(node: any): string {
  if (node.value) return node.value;
  return (node.children ?? []).map(textOf).join("");
}

export type Skill = {
  name: string;
  description: string;
  summary: string;
  group: string;
  body: Rendered;
};

// One-line summaries from the guide's skill table, so the cards say what the guide says.
function guideSummaries(): Record<string, string> {
  const guide = fs.readFileSync(path.join(ROOT, "docs/guide.md"), "utf8");
  const out: Record<string, string> = {};
  for (const m of guide.matchAll(/^\| `([a-z-]+)` \| (.+?) \|$/gm)) out[m[1]] = m[2];
  return out;
}

// Renders a one-line summary's `code` spans as HTML, escaping everything else.
export function inlineHtml(text: string): string {
  const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped.replace(/`([^`]+)`/g, "<code>$1</code>");
}

function firstSentence(text: string): string {
  return text.match(/^.*?\.(\s|$)/)?.[0].trim() ?? text;
}

let cache: Skill[] | undefined;

export function skills(): Skill[] {
  if (cache) return cache;
  const names = fs
    .readdirSync(path.join(ROOT, "skills"))
    .filter((n) => fs.existsSync(path.join(ROOT, "skills", n, "SKILL.md")))
    .sort();
  const grouped = Object.fromEntries(GROUPS.flatMap((g) => g.skills.map((s) => [s, g.title])));
  const missing = names.filter((n) => !grouped[n]);
  const unknown = Object.keys(grouped).filter((n) => !names.includes(n));
  if (missing.length || unknown.length) {
    throw new Error(
      `website/src/lib/groups.ts is out of step with skills/: ` +
        `not in a group: ${missing.join(", ") || "none"}; no such skill: ${unknown.join(", ") || "none"}`,
    );
  }
  const summaries = guideSummaries();
  cache = names.map((name) => {
    const source = `skills/${name}/SKILL.md`;
    const raw = fs.readFileSync(path.join(ROOT, source), "utf8");
    const fm = raw.match(/^---\n([\s\S]*?)\n---\n/);
    const meta = fm ? parseYaml(fm[1]) : {};
    const description: string = meta.description ?? "";
    return {
      name,
      description,
      summary: summaries[name] ?? firstSentence(description),
      group: grouped[name],
      body: renderMarkdown(fm ? raw.slice(fm[0].length) : raw, source),
    };
  });
  return cache;
}
