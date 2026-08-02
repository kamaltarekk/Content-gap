import { runPipeline } from "@cgi/analysis-engine";
import { closeDb, getDb, projects, runMigrations } from "@cgi/database";
import { createEmbeddingProvider, createLlmProvider } from "@cgi/llm";
import { type AnalyzeJob, QUEUE_ANALYZE, QUEUE_WEEKLY_REFRESH, loadConfig } from "@cgi/shared";
import PgBoss from "pg-boss";
import { refreshProject } from "./refresh.js";

// Worker: consumes analyze jobs and runs the weekly refresh on a schedule. Runs independently
// of the API and the extension (so analysis continues when the extension is closed).

async function main() {
  const config = loadConfig();
  await runMigrations();
  const db = getDb();
  const llm = createLlmProvider(config);
  const embed = createEmbeddingProvider(config);

  const boss = new PgBoss({ connectionString: config.databaseUrl });
  boss.on("error", (err) => console.error("pg-boss error", err));
  await boss.start();
  await boss.createQueue(QUEUE_ANALYZE);
  await boss.createQueue(QUEUE_WEEKLY_REFRESH);

  await boss.work<AnalyzeJob>(QUEUE_ANALYZE, async (jobs) => {
    for (const job of jobs) {
      const { projectId, triggerType } = job.data;
      console.log(`[analyze] project=${projectId} trigger=${triggerType}`);
      const res = await runPipeline(projectId, triggerType, { db, llm, embed, config });
      console.log(`[analyze] project=${projectId} status=${res.status} published=${res.publishedGapIds.length}`);
    }
  });

  await boss.work(QUEUE_WEEKLY_REFRESH, async () => {
    const allProjects = await db.select({ id: projects.id }).from(projects);
    for (const p of allProjects) {
      const result = await refreshProject(db, p.id, config);
      console.log(`[weekly-refresh] project=${p.id} checked=${result.checked} changed=${result.changed.length} failed=${result.failed.length}`);
      if (result.changed.length > 0) {
        await boss.send(QUEUE_ANALYZE, { projectId: p.id, triggerType: "WEEKLY_REFRESH" } satisfies AnalyzeJob);
      }
    }
  });

  // Weekly schedule (Mondays 06:00 UTC). Per-project day/time is stored on the project and can
  // refine this later; v0 uses a single weekly sweep across projects.
  await boss.schedule(QUEUE_WEEKLY_REFRESH, "0 6 * * 1");

  console.log("Worker started: consuming analyze jobs + weekly refresh scheduled (Mon 06:00 UTC).");

  const shutdown = async () => {
    await boss.stop();
    await closeDb();
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
