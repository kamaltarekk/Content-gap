import { runPipeline } from "@cgi/analysis-engine";
import { closeDb, gapEvidence, gaps, getDb, runMigrations, seedDemo } from "@cgi/database";
import { createEmbeddingProvider, createLlmProvider } from "@cgi/llm";
import { loadConfig } from "@cgi/shared";
import { and, eq } from "drizzle-orm";

// `pnpm demo` entry: migrate -> seed -> run the full pipeline with fake providers -> print
// the <=10 verified gaps. No Anthropic key required.

async function main() {
  const config = loadConfig();
  await runMigrations();
  const db = getDb();
  const { projectId, token } = await seedDemo(db);
  const res = await runPipeline(projectId, "MANUAL_SETUP", {
    db,
    llm: createLlmProvider(config),
    embed: createEmbeddingProvider(config),
    config,
    referenceDate: "2026-08-02",
  });

  const published = await db.select().from(gaps).where(and(eq(gaps.projectId, projectId), eq(gaps.status, "PUBLISHED")));
  published.sort((a, b) => b.priorityScore - a.priorityScore);

  console.log(`\n=== Content Gap Intelligence — demo run ===`);
  console.log(`project=${projectId} status=${res.status} publishedGaps=${published.length} (cap 10)\n`);
  for (const g of published) {
    const ev = await db.select().from(gapEvidence).where(eq(gapEvidence.gapId, g.id));
    console.log(`• [${g.priorityLabel}] score=${g.priorityScore} ${g.gapType} (${g.evidenceStatus}) — ${g.title}`);
    console.log(`  ${ev.length} verified evidence item(s); coverage: ${g.currentCoverageSummary}`);
  }
  console.log(`\nExtension project token (configure in the extension): ${token}\n`);
  await closeDb();
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
