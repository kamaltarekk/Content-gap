import { createEmbeddingProvider, createLlmProvider } from "@cgi/llm";
import { runPipeline } from "@cgi/analysis-engine";
import { getDb } from "@cgi/database";
import { type AnalyzeJob, QUEUE_ANALYZE, loadConfig } from "@cgi/shared";

// Job queue abstraction. In production the API enqueues to pg-boss and the worker consumes.
// When pg-boss is unavailable (e.g. integration tests), an inline queue runs the pipeline in
// the background so ingestion still auto-triggers analysis without a manual button.

export interface Queue {
  enqueueAnalyze(job: AnalyzeJob): Promise<void>;
  stop(): Promise<void>;
}

export class InlineQueue implements Queue {
  private running = new Set<Promise<unknown>>();
  async enqueueAnalyze(job: AnalyzeJob): Promise<void> {
    const p = (async () => {
      const config = loadConfig();
      await runPipeline(job.projectId, job.triggerType, {
        db: getDb(),
        llm: createLlmProvider(config),
        embed: createEmbeddingProvider(config),
        config,
      });
    })().catch(() => undefined);
    this.running.add(p);
    void p.finally(() => this.running.delete(p));
  }
  async drain(): Promise<void> {
    await Promise.allSettled([...this.running]);
  }
  async stop(): Promise<void> {
    await this.drain();
  }
}

export class PgBossQueue implements Queue {
  private constructor(private boss: import("pg-boss")) {}
  static async create(connectionString: string): Promise<PgBossQueue> {
    const PgBoss = (await import("pg-boss")).default;
    const boss = new PgBoss({ connectionString });
    await boss.start();
    await boss.createQueue(QUEUE_ANALYZE);
    return new PgBossQueue(boss as unknown as import("pg-boss"));
  }
  async enqueueAnalyze(job: AnalyzeJob): Promise<void> {
    await (this.boss as any).send(QUEUE_ANALYZE, job, { singletonKey: job.projectId, singletonSeconds: 5 });
  }
  async stop(): Promise<void> {
    await (this.boss as any).stop();
  }
}

export async function createQueue(): Promise<Queue> {
  const config = loadConfig();
  if (process.env.USE_INLINE_QUEUE === "true") return new InlineQueue();
  try {
    return await PgBossQueue.create(config.databaseUrl);
  } catch {
    return new InlineQueue();
  }
}
