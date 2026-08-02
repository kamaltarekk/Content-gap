import { describe, expect, it } from "vitest";
import { offsetsValid, verifyQuote } from "../src/verify-evidence.js";
import { selectShadowSample } from "../src/shadow-sample.js";
import { keywordOverlap } from "../src/retrieval.js";

describe("evidence verification (exact-substring)", () => {
  const chunk = "The buyer worried it's too complex to implement. غالية جدا.";
  it("verifies an exact substring with valid offsets", () => {
    const v = verifyQuote(chunk, "too complex to implement");
    expect(v.verified).toBe(true);
    expect(chunk.slice(v.startOffset, v.endOffset)).toBe("too complex to implement");
    expect(offsetsValid(chunk, v.startOffset, v.endOffset)).toBe(true);
  });
  it("verifies a whitespace-normalized equivalent with real offsets", () => {
    const v = verifyQuote(chunk, "too   complex  to implement");
    expect(v.verified).toBe(true);
    expect(v.normalized).toBe(true);
    expect(chunk.slice(v.startOffset, v.endOffset)).toBe("too complex to implement");
  });
  it("rejects a quote that is not present (no fabricated evidence)", () => {
    const v = verifyQuote(chunk, "we guarantee number one results");
    expect(v.verified).toBe(false);
  });
  it("verifies Arabic substrings", () => {
    const v = verifyQuote(chunk, "غالية جدا");
    expect(v.verified).toBe(true);
  });
});

describe("shadow sample selection", () => {
  const pool = Array.from({ length: 10 }, (_, i) => ({ id: `cand-${i}` }));
  it("selects at least min(5, ceil(20%)) deterministically", () => {
    const a = selectShadowSample(pool, "run-1");
    const b = selectShadowSample(pool, "run-1");
    expect(a).toEqual(b); // deterministic
    expect(a.length).toBe(2); // ceil(20% of 10) = 2, min(5, 2) = 2
  });
  it("changes with the run id", () => {
    const a = selectShadowSample(pool, "run-1").map((x) => x.id);
    const b = selectShadowSample(pool, "run-2").map((x) => x.id);
    expect(a).not.toEqual(b);
  });
  it("handles an empty pool", () => {
    expect(selectShadowSample([], "r")).toEqual([]);
  });
});

describe("keyword overlap gate", () => {
  it("requires a shared >=4-char token", () => {
    expect(keywordOverlap("implementation workflow", "rebuild the workflow")).toBe(true);
    expect(keywordOverlap("pricing", "الإعلان")).toBe(false);
  });
});
