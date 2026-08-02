import { Fetcher } from "@cgi/crawler";
import { type Db, sources } from "@cgi/database";
import { ingestContent } from "@cgi/analysis-engine";
import { type AppConfig, type OwnerType } from "@cgi/shared";
import { and, eq } from "drizzle-orm";

// Weekly refresh: re-fetch active URL sources, hash-diff, and report which changed so the
// caller can queue targeted reprocessing. Deterministic control flow; network via Fetcher.
// `fetchOverride` lets tests inject content without real network access.

export interface RefreshResult {
  projectId: string;
  checked: number;
  changed: string[];
  failed: { sourceId: string; error: string }[];
}

export async function refreshProject(
  db: Db,
  projectId: string,
  config: AppConfig,
  fetchOverride?: (url: string) => Promise<{ ok: boolean; title: string; text: string; error?: string }>,
): Promise<RefreshResult> {
  const fetcher = new Fetcher(config);
  const rows = await db
    .select()
    .from(sources)
    .where(and(eq(sources.projectId, projectId), eq(sources.refreshEnabled, true)));
  const urlSources = rows.filter((s) => s.crawlMethod === "HTTP" && s.canonicalUrl);

  const changed: string[] = [];
  const failed: { sourceId: string; error: string }[] = [];
  for (const s of urlSources) {
    try {
      const res = fetchOverride ? await fetchOverride(s.canonicalUrl!) : await fetcher.fetchUrl(s.canonicalUrl!);
      if (!res.ok) {
        failed.push({ sourceId: s.id, error: res.error ?? "fetch_failed" });
        await db.update(sources).set({ status: "FAILED", lastFailureAt: new Date(), errorMessage: res.error ?? "fetch_failed" }).where(eq(sources.id, s.id));
        continue; // one failed source must not invalidate others
      }
      const { changed: didChange } = await ingestContent(db, {
        projectId,
        ownerType: s.ownerType as OwnerType,
        competitorSlot: s.competitorSlot,
        sourceType: s.sourceType,
        name: s.name,
        url: s.canonicalUrl,
        title: res.title,
        text: res.text,
        crawlMethod: "HTTP",
      });
      if (didChange) changed.push(s.id);
    } catch (err) {
      failed.push({ sourceId: s.id, error: (err as Error).message });
    }
  }
  return { projectId, checked: urlSources.length, changed, failed };
}
