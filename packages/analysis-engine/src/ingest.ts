import { type Db, sourceSnapshots, sources } from "@cgi/database";
import { type OwnerType, contentHash } from "@cgi/shared";
import { and, eq } from "drizzle-orm";

// Deterministic, idempotent ingestion of raw content into a source + hash-gated snapshot.
// Returns whether a NEW snapshot was created (i.e. content changed) so callers can decide
// whether to trigger analysis.

export interface IngestInput {
  projectId: string;
  ownerType: OwnerType;
  competitorSlot: number | null;
  sourceType: string;
  name: string;
  url: string | null;
  title: string;
  text: string;
  crawlMethod: string;
  publishedAt?: string | null;
}

export async function ingestContent(db: Db, input: IngestInput): Promise<{ sourceId: string; changed: boolean }> {
  // Reuse an existing source with the same owner + canonical URL, else create one.
  let sourceId: string;
  const existing = input.url
    ? await db
        .select({ id: sources.id })
        .from(sources)
        .where(and(eq(sources.projectId, input.projectId), eq(sources.ownerType, input.ownerType), eq(sources.canonicalUrl, input.url)))
        .limit(1)
    : [];
  if (existing[0]) {
    sourceId = existing[0].id;
  } else {
    const [src] = await db
      .insert(sources)
      .values({
        projectId: input.projectId,
        ownerType: input.ownerType,
        competitorSlot: input.competitorSlot,
        sourceType: input.sourceType,
        name: input.name,
        canonicalUrl: input.url,
        crawlMethod: input.crawlMethod,
        status: "PENDING",
      })
      .returning({ id: sources.id });
    sourceId = src!.id;
  }

  const hash = contentHash(input.text);
  const current = await db
    .select({ id: sourceSnapshots.id, contentHash: sourceSnapshots.contentHash })
    .from(sourceSnapshots)
    .where(and(eq(sourceSnapshots.sourceId, sourceId), eq(sourceSnapshots.isCurrent, true)))
    .limit(1);

  // Hash-gated: unchanged content creates no new snapshot and does not reprocess.
  if (current[0]?.contentHash === hash) {
    await db.update(sources).set({ lastSuccessAt: new Date(), status: "PROCESSED" }).where(eq(sources.id, sourceId));
    return { sourceId, changed: false };
  }

  // Retire old current snapshot, add the new one.
  await db.update(sourceSnapshots).set({ isCurrent: false }).where(and(eq(sourceSnapshots.sourceId, sourceId), eq(sourceSnapshots.isCurrent, true)));
  await db.insert(sourceSnapshots).values({
    sourceId,
    contentHash: hash,
    rawContent: input.text,
    normalizedContent: input.text,
    metadataJson: { title: input.title, publishedAt: input.publishedAt ?? null, competitorSlot: input.competitorSlot },
    isCurrent: true,
  });
  await db.update(sources).set({ lastSuccessAt: new Date(), status: "PROCESSED" }).where(eq(sources.id, sourceId));
  return { sourceId, changed: true };
}
