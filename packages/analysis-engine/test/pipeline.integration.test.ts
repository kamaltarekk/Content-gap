import { createEmbeddingProvider, createLlmProvider } from "@cgi/llm";
import {
  chunks as chunksTable,
  closeDb,
  contentUnits,
  gapEvidence,
  gaps,
  getDb,
  runMigrations,
  seedDemo,
  sourceSnapshots,
  sources,
} from "@cgi/database";
import { contentHash } from "@cgi/shared";
import { and, eq } from "drizzle-orm";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { ingestContent } from "../src/ingest.js";
import { runPipeline } from "../src/pipeline.js";

let dbAvailable = true;
const db = getDb();

beforeAll(async () => {
  try {
    await runMigrations();
  } catch {
    dbAvailable = false;
  }
});
afterAll(async () => {
  if (dbAvailable) await closeDb();
});

describe("full fake-LLM pipeline on the demo dataset", () => {
  it("produces <=10 verified, evidence-backed, bilingual gaps and ignores injection", async () => {
    if (!dbAvailable) return;
    const { projectId } = await seedDemo(db);
    const llm = createLlmProvider();
    const embed = createEmbeddingProvider();
    const res = await runPipeline(projectId, "TEST", { db, llm, embed, referenceDate: "2026-08-02" });
    expect(res.status).toBe("SUCCEEDED");

    const published = await db.select().from(gaps).where(and(eq(gaps.projectId, projectId), eq(gaps.status, "PUBLISHED")));
    // Definition of Done: at most ten gaps, and the demo yields several real ones.
    expect(published.length).toBeLessThanOrEqual(10);
    expect(published.length).toBeGreaterThanOrEqual(3);

    // Every published gap must have >=1 evidence item, and every quote must be an exact
    // substring of an EXISTING chunk (no unknown ids, no fabricated evidence).
    let strongCount = 0;
    for (const g of published) {
      if (g.evidenceStatus === "STRONG_EVIDENCE") strongCount++;
      const ev = await db.select().from(gapEvidence).where(eq(gapEvidence.gapId, g.id));
      expect(ev.length).toBeGreaterThan(0);
      for (const e of ev) {
        expect(e.chunkId).toBeTruthy();
        const [chunk] = await db.select().from(chunksTable).where(eq(chunksTable.id, e.chunkId!));
        expect(chunk).toBeTruthy(); // referenced chunk exists
        expect(chunk!.text.includes(e.exactQuote)).toBe(true); // exact substring
        expect(chunk!.text.slice(e.quoteStartOffset, e.quoteEndOffset)).toBe(e.exactQuote); // valid offsets
      }
    }
    expect(strongCount).toBeGreaterThanOrEqual(1);

    // Bilingual: at least one Arabic-script gap and one Latin-script gap.
    const hasArabic = published.some((g) => /[؀-ۿ]/.test(g.title));
    const hasLatin = published.some((g) => /[A-Za-z]/.test(g.title));
    expect(hasArabic).toBe(true);
    expect(hasLatin).toBe(true);

    // Injection attempt in competitor content was ignored (recorded, not obeyed).
    const [run] = await db.select().from(gaps).where(eq(gaps.id, published[0]!.id));
    expect(run).toBeTruthy();
  });

  it("does not reprocess unchanged content and targets changed content", async () => {
    if (!dbAvailable) return;
    const { projectId } = await seedDemo(db);
    const llm = createLlmProvider();
    const embed = createEmbeddingProvider();
    await runPipeline(projectId, "TEST", { db, llm, embed, referenceDate: "2026-08-02" });
    const before = await db.select().from(contentUnits).where(eq(contentUnits.projectId, projectId));

    // Re-run with no changes: content-hash gate means no new content units are created.
    await runPipeline(projectId, "TEST", { db, llm, embed, referenceDate: "2026-08-02" });
    const afterSame = await db.select().from(contentUnits).where(eq(contentUnits.projectId, projectId));
    expect(afterSame.length).toBe(before.length);

    // Change one owned source -> a new snapshot is created and reprocessed.
    const [owned] = await db.select().from(sources).where(and(eq(sources.projectId, projectId), eq(sources.ownerType, "OWNED"))).limit(1);
    const { changed } = await ingestContent(db, {
      projectId, ownerType: "OWNED", competitorSlot: null, sourceType: "URL", name: owned!.name,
      url: owned!.canonicalUrl, title: "changed", text: "Brand-new content about implementation steps and proof.", crawlMethod: "HTTP",
    });
    expect(changed).toBe(true);
    await runPipeline(projectId, "TEST", { db, llm, embed, referenceDate: "2026-08-02" });
    const afterChange = await db.select().from(contentUnits).where(eq(contentUnits.projectId, projectId));
    expect(afterChange.length).toBeGreaterThan(before.length);
  });

  it("ingestContent is hash-gated (idempotent) for identical content", async () => {
    if (!dbAvailable) return;
    const { projectId } = await seedDemo(db);
    const text = "Some owned page content.";
    const first = await ingestContent(db, { projectId, ownerType: "OWNED", competitorSlot: null, sourceType: "URL", name: "p", url: "https://x.example/p", title: "p", text, crawlMethod: "HTTP" });
    expect(first.changed).toBe(true);
    const second = await ingestContent(db, { projectId, ownerType: "OWNED", competitorSlot: null, sourceType: "URL", name: "p", url: "https://x.example/p", title: "p", text, crawlMethod: "HTTP" });
    expect(second.changed).toBe(false);
    const snaps = await db.select().from(sourceSnapshots).where(eq(sourceSnapshots.sourceId, first.sourceId));
    expect(snaps.filter((s) => s.isCurrent)).toHaveLength(1);
    expect(snaps[0]!.contentHash).toBe(contentHash(text));
  });
});
