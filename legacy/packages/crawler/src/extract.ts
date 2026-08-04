import { Readability } from "@mozilla/readability";
import * as cheerio from "cheerio";
import { JSDOM } from "jsdom";

export interface ExtractedPage {
  title: string;
  text: string;
  method: "readability" | "cheerio";
}

/**
 * Deterministic HTML -> clean text. Try Readability first (article-quality extraction),
 * fall back to Cheerio (strip script/style/nav, collapse whitespace).
 */
export function extractFromHtml(html: string, url: string): ExtractedPage {
  try {
    const dom = new JSDOM(html, { url });
    const reader = new Readability(dom.window.document);
    const article = reader.parse();
    if (article && article.textContent && article.textContent.trim().length > 120) {
      return { title: (article.title ?? "").trim(), text: normalizeText(article.textContent), method: "readability" };
    }
  } catch {
    // fall through to cheerio
  }
  const $ = cheerio.load(html);
  $("script, style, noscript, nav, footer, header, svg").remove();
  const title = $("title").first().text().trim() || $("h1").first().text().trim();
  const text = normalizeText($("body").text() || $.root().text());
  return { title, text, method: "cheerio" };
}

export function normalizeText(text: string): string {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .split("\n")
    .map((l) => l.trim())
    .join("\n")
    .trim();
}
