// The site search index: one entry per section of every page, built with the site.
import fs from "node:fs";
import path from "node:path";
import { renderFile, skills } from "../lib/content";

declare const __REPO_ROOT__: string;

type Entry = { url: string; page: string; heading: string; id: string; text: string };

const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"' };

function plain(html: string): string {
  return html
    .replace(/<\/?(a|code|strong|em|span)\b[^>]*>/g, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&(amp|lt|gt|quot);/g, (_, e) => ENTITIES[e])
    .replace(/\s+/g, " ")
    .trim();
}

// Splits a page's HTML at each h2 and h3, so a result can jump to its section.
function sections(url: string, page: string, intro: string, html: string): Entry[] {
  const out: Entry[] = [];
  const parts = html.split(/(<h[23][^>]*>[\s\S]*?<\/h[23]>)/);
  out.push({ url, page, heading: "", id: "", text: plain(`${intro} ${parts[0]}`) });
  for (let i = 1; i < parts.length; i += 2) {
    const id = parts[i].match(/\sid="([^"]+)"/)?.[1] ?? "";
    out.push({ url, page, heading: plain(parts[i]), id, text: plain(parts[i + 1] ?? "") });
  }
  return out;
}

// The home page is hand-written, so its static HTML is read from the page itself.
function homeHtml(): string {
  let src = fs.readFileSync(path.join(__REPO_ROOT__, "website/src/pages/index.astro"), "utf8").replace(/^---[\s\S]*?---/, "");
  // Drops {expressions} innermost first; the skill cards they render are indexed as skill pages.
  while (/\{[^{}]*\}/.test(src)) src = src.replace(/\{[^{}]*\}/g, "");
  return src.replace(/<h1[\s\S]*?<\/h1>/, "");
}

export function GET() {
  const entries: Entry[] = [
    ...sections("/", "Jig", "", homeHtml()),
    ...sections("/guide/", "Guide", "", renderFile("docs/guide.md").html),
    ...sections("/glossary/", "Glossary", "", renderFile("GLOSSARY.md").html),
    ...sections("/decisions/", "Decisions", "", renderFile("docs/decisions.md").html),
    ...skills().flatMap((s) => sections(`/skills/${s.name}/`, `/${s.name}`, `${s.summary} ${s.description}`, s.body.html)),
  ];
  return new Response(JSON.stringify(entries), { headers: { "Content-Type": "application/json" } });
}
