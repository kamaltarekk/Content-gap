import { describe, expect, it } from "vitest";
import {
  classifyEvidenceStatus,
  computePriorityScore,
  contentHash,
  MAX_PRIORITY_SCORE,
  normalizeUrl,
  parseDateOrNull,
  priorityLabelFor,
  UnknownIdError,
  validateIdReferences,
} from "../src/index.js";

describe("url normalization", () => {
  it("canonicalizes host, ports, tracking params, trailing slash", () => {
    expect(normalizeUrl("HTTPS://Example.com:443/path/?utm_source=x&b=2&a=1#frag")).toBe(
      "https://example.com/path?a=1&b=2",
    );
  });
  it("keeps root slash and is idempotent", () => {
    const once = normalizeUrl("http://example.com/");
    expect(normalizeUrl(once)).toBe(once);
  });
});

describe("content hashing", () => {
  it("is stable under CRLF, repeated spaces, extra blank lines, trailing space", () => {
    expect(contentHash("a   b\r\n\r\n\r\ndone  ")).toBe(contentHash("a b\n\ndone"));
  });
  it("differs for different content", () => {
    expect(contentHash("a")).not.toBe(contentHash("b"));
  });
});

describe("date parsing", () => {
  it("parses ISO and returns null for junk", () => {
    expect(parseDateOrNull("2019-03-01T10:00:00Z")).toBe("2019-03-01");
    expect(parseDateOrNull("not a date")).toBeNull();
  });
});

describe("priority formula", () => {
  it("matches the documented weighted sum and max", () => {
    const full = {
      commercialImpact: 5, journeyBlockage: 5, cohortPriority: 5, demandStrength: 5, coverageDeficit: 5,
      strategicAlignment: 5, competitiveOpportunity: 5, actionability: 5, productionFeasibility: 5, learningValue: 5,
    };
    expect(computePriorityScore(full)).toBe(MAX_PRIORITY_SCORE);
    expect(MAX_PRIORITY_SCORE).toBe(90);
  });
  it("labels by threshold and rejects when flagged", () => {
    expect(priorityLabelFor(90)).toBe("P0_CRITICAL_BLOCKER");
    expect(priorityLabelFor(0)).toBe("P5_REJECT");
    expect(priorityLabelFor(90, true)).toBe("P5_REJECT");
  });
});

describe("evidence status rules (no numeric confidence)", () => {
  it("STRONG needs >=2 independent verified items incl. first-party and insufficient coverage", () => {
    const r = classifyEvidenceStatus(
      [
        { role: "CUSTOMER_DEMAND", ownerType: "VOC", verified: true },
        { role: "STRATEGIC_PRIORITY", ownerType: "BUSINESS_BRIEF", verified: true },
      ],
      "NONE",
    );
    expect(r.status).toBe("STRONG_EVIDENCE");
    expect(r.ruleId).toContain("STRONG");
  });
  it("competitor-only evidence is a HYPOTHESIS", () => {
    const r = classifyEvidenceStatus([{ role: "COMPETITOR_CONTEXT", ownerType: "COMPETITOR", verified: true }], "NONE");
    expect(r.status).toBe("HYPOTHESIS");
  });
});

describe("id-reference guard (prompt-injection / hallucination defense)", () => {
  const allowed = { chunkIds: new Set(["c1"]), cohortIds: new Set(["k1"]), contentUnitIds: new Set(["u1"]) };
  it("passes when all ids are known", () => {
    expect(() => validateIdReferences({ evidenceChunkId: "c1", cohortId: "k1", contentUnitId: "u1" }, allowed)).not.toThrow();
  });
  it("throws UnknownIdError on a stray chunk id", () => {
    expect(() => validateIdReferences({ chunkId: "ROGUE" }, allowed)).toThrow(UnknownIdError);
  });
});
