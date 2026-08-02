import { parseDateOrNull, type VocRow, VocRowSchema } from "@cgi/shared";
import * as cheerio from "cheerio";

// Deterministic file parsers for uploaded owned/VoC/competitor content.

export function parseTxtOrMd(content: string, name: string): { title: string; text: string } {
  const firstHeading = /^#\s+(.+)$/m.exec(content);
  const title = firstHeading?.[1]?.trim() ?? name;
  return { title, text: content.trim() };
}

/** CSV parser (RFC-4180-ish: quotes, escaped quotes, commas/newlines in quotes). */
export function parseCsv(content: string): Record<string, string>[] {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  for (let i = 0; i < content.length; i++) {
    const c = content[i]!;
    if (inQuotes) {
      if (c === '"') {
        if (content[i + 1] === '"') {
          field += '"';
          i++;
        } else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && content[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      if (row.some((f) => f.length > 0)) rows.push(row);
      row = [];
    } else field += c;
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    if (row.some((f) => f.length > 0)) rows.push(row);
  }
  if (rows.length === 0) return [];
  const headers = rows[0]!.map((h) => h.trim());
  return rows.slice(1).map((r) => {
    const obj: Record<string, string> = {};
    headers.forEach((h, idx) => (obj[h] = (r[idx] ?? "").trim()));
    return obj;
  });
}

/** Normalize arbitrary VoC rows (from CSV/JSON) into validated VocRow[]. Missing columns are fine. */
export function normalizeVocRows(rows: Record<string, unknown>[]): { rows: VocRow[]; skipped: number } {
  const out: VocRow[] = [];
  let skipped = 0;
  for (const r of rows) {
    const text = pick(r, ["text", "quote", "message", "comment", "body", "content"]);
    if (!text) {
      skipped++;
      continue;
    }
    const candidate = {
      text,
      sourceType: pick(r, ["sourceType", "source_type", "source", "channel"]) || undefined,
      date: parseDateOrNull(pick(r, ["date", "created_at", "timestamp"])) || undefined,
      customerType: pick(r, ["customerType", "customer_type", "persona"]) || undefined,
      outcome: pick(r, ["outcome", "result"]) || undefined,
      tags: splitTags(pick(r, ["tags", "labels"])),
    };
    const parsed = VocRowSchema.safeParse(candidate);
    if (parsed.success) out.push(parsed.data);
    else skipped++;
  }
  return { rows: out, skipped };
}

export function parseSitemap(xml: string): string[] {
  const $ = cheerio.load(xml, { xmlMode: true });
  const urls: string[] = [];
  $("url > loc, sitemap > loc").each((_, el) => {
    const loc = $(el).text().trim();
    if (loc) urls.push(loc);
  });
  return urls;
}

function pick(row: Record<string, unknown>, keys: string[]): string {
  for (const k of keys) {
    const v = row[k] ?? row[k.toLowerCase()];
    if (typeof v === "string" && v.trim()) return v.trim();
    if (typeof v === "number") return String(v);
  }
  return "";
}
function splitTags(raw: string): string[] | undefined {
  if (!raw) return undefined;
  return raw
    .split(/[;,|]/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 30);
}
