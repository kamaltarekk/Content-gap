/**
 * End-to-end demo runner: migrate -> seed -> run the full pipeline with FAKE providers
 * (no Anthropic key) -> print the published gaps, coverage, evidence, and usage.
 * This is the fixture-driven full-pipeline check referenced by the DoD.
 */
import { createEmbeddingProvider, createLlmProvider } from "@cgi/llm";
import { runPipeline } from "@cgi/analysis-engine";
import { closeDb, gapEvidence, gaps, getDb, runMigrations, seedDemo } from "@cgi/database";
import { and, eq } from "drizzle-orm";

async function main() {
  await runMigrations();
  const db = getDb();
  const { projectId, token } = await seedDemo(db);
  console.log(`\nSeeded demo project ${projectId}`);

  const llm = createLlmProvider();
  const embed = createEmbeddingProvider();
  const referenceDate = "2026-08-02";
  const res = await runPipeline(projectId, "MANUAL_SETUP", { db, llm, embed, referenceDate });
  console.log(`\nPipeline status: ${res.status}; published ${res.publishedGapIds.length} gap(s)\n`);

  const published = await db.select().from(gaps).where(and(eq(gaps.projectId, projectId), eq(gaps.status, "PUBLISHED")));
  published.sort((a, b) => b.priorityScore - a.priorityScore);
  for (const g of published) {
    const ev = await db.select().from(gapEvidence).where(eq(gapEvidence.gapId, g.id));
    console.log(`• [${g.priorityLabel}] score=${g.priorityScore} ${g.gapType} — ${g.title}`);
    console.log(`  evidenceStatus=${g.evidenceStatus} | stage=${g.journeyStage} | evidence items=${ev.length}`);
    for (const e of ev.slice(0, 2)) {
      console.log(`    [${e.evidenceRole}] "${e.exactQuote.slice(0, 80)}"`);
    }
  }
  console.log(`\nExtension project token: ${token}`);
  await closeDb();
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
