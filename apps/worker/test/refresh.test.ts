import { closeDb, getDb, runMigrations, seedDemo, sources, sourceSnapshots } from "@cgi/database";
import { loadConfig } from "@cgi/shared";
import { and, eq } from "drizzle-orm";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { refreshProject } from "../src/refresh.js";

let dbAvailable = true;
let projectId = "";
const db = getDb();
const config = loadConfig();

beforeAll(async () => {
  try {
    await runMigrations();
    projectId = (await seedDemo(db)).projectId;
  } catch {
    dbAvailable = false;
  }
});
afterAll(async () => {
  if (dbAvailable) await closeDb();
});

async function currentTextByUrl(url: string): Promise<string> {
  const [row] = await db
    .select({ text: sourceSnapshots.normalizedContent })
    .from(sourceSnapshots)
    .innerJoin(sources, eq(sourceSnapshots.sourceId, sources.id))
    .where(and(eq(sources.canonicalUrl, url), eq(sourceSnapshots.isCurrent, true)))
    .limit(1);
  return row?.text ?? "";
}

describe("weekly refresh (hash-gated, failure-isolated)", () => {
  it("does not reprocess when content is unchanged", async () => {
    if (!dbAvailable) return;
    const res = await refreshProject(db, projectId, config, async (url) => ({ ok: true, title: "", text: await currentTextByUrl(url) }));
    expect(res.checked).toBeGreaterThan(0);
    expect(res.changed).toHaveLength(0);
    expect(res.failed).toHaveLength(0);
  });

  it("detects changed content and isolates a failed source", async () => {
    if (!dbAvailable) return;
    // Pick one HTTP source to fail; everything else returns brand-new content.
    const httpSources = await db.select().from(sources).where(and(eq(sources.projectId, projectId), eq(sources.crawlMethod, "HTTP")));
    const failUrl = httpSources[0]!.canonicalUrl!;
    const res = await refreshProject(db, projectId, config, async (url) => {
      if (url === failUrl) return { ok: false, title: "", text: "", error: "HTTP 503" };
      return { ok: true, title: "", text: `fresh content for ${url} about implementation proof` };
    });
    // One failed source is recorded; it does not invalidate the others, which changed.
    expect(res.failed.map((f) => f.sourceId)).toContain(httpSources[0]!.id);
    expect(res.changed.length).toBe(res.checked - 1);
    const [failed] = await db.select().from(sources).where(eq(sources.id, httpSources[0]!.id));
    expect(failed!.status).toBe("FAILED");
  });
});
