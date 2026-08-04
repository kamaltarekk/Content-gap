import { describe, expect, it } from "vitest";
import { extractFromHtml } from "../src/extract.js";
import { normalizeVocRows, parseCsv, parseSitemap } from "../src/parsers.js";
import { PerDomainRateLimiter, type Clock } from "../src/rate-limiter.js";

describe("csv parsing", () => {
  it("handles quotes, escaped quotes, and embedded commas", () => {
    const rows = parseCsv('text,date\n"Hello, ""world""",2020-01-01\nsecond,2020-02-02');
    expect(rows).toHaveLength(2);
    expect(rows[0]!.text).toBe('Hello, "world"');
    expect(rows[1]!.date).toBe("2020-02-02");
  });
});

describe("voc normalization", () => {
  it("works when optional columns are missing", () => {
    const { rows, skipped } = normalizeVocRows([{ text: "غالية جدا" }, { note: "no text field" }]);
    expect(rows).toHaveLength(1);
    expect(skipped).toBe(1);
  });
});

describe("html extraction", () => {
  it("falls back to cheerio for thin markup and strips scripts", () => {
    const res = extractFromHtml("<html><head><title>T</title></head><body><script>bad()</script><p>Real content here that is long enough to keep.</p></body></html>", "https://x.example/");
    expect(res.text).toContain("Real content here");
    expect(res.text).not.toContain("bad()");
  });
});

describe("sitemap parsing", () => {
  it("extracts loc urls", () => {
    const urls = parseSitemap("<urlset><url><loc>https://a.example/1</loc></url><url><loc>https://a.example/2</loc></url></urlset>");
    expect(urls).toEqual(["https://a.example/1", "https://a.example/2"]);
  });
});

describe("per-domain rate limiter", () => {
  it("spaces requests by the min interval using an injected clock", async () => {
    let now = 0;
    const waits: number[] = [];
    const clock: Clock = { now: () => now, sleep: async (ms) => { waits.push(ms); now += ms; } };
    const limiter = new PerDomainRateLimiter(1, clock); // 1 rps -> 1000ms spacing
    await limiter.acquire("a.example");
    await limiter.acquire("a.example");
    expect(waits[0]).toBe(1000);
  });
});
