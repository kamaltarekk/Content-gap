import { randomBytes } from "node:crypto";
import { contentHash, sha256 } from "@cgi/shared";
import { type DemoAsset, demoDataset } from "@cgi/test-fixtures";
import { eq } from "drizzle-orm";
import { getDb } from "./client.js";
import {
  businessBriefs,
  cohorts,
  offers,
  projectTokens,
  projects,
  sourceSnapshots,
  sources,
} from "./schema.js";

// Seeds the synthetic demo project as raw sources + snapshots. The pipeline (worker/api) then
// ingests and analyzes them. Idempotent: removes an existing demo project of the same name first.

export async function seedDemo(db = getDb()): Promise<{ projectId: string; token: string; tokenId: string }> {
  const d = demoDataset;

  const existing = await db.select({ id: projects.id }).from(projects).where(eq(projects.name, d.project.name));
  for (const p of existing) {
    await db.delete(projects).where(eq(projects.id, p.id)); // cascades
  }

  const [project] = await db
    .insert(projects)
    .values({
      name: d.project.name,
      primaryDomain: d.project.primaryDomain,
      defaultLanguage: d.project.defaultLanguage,
      refreshSchedule: d.project.refreshSchedule,
    })
    .returning();
  const projectId = project!.id;

  await db.insert(businessBriefs).values({ projectId, structuredDataJson: d.brief, markdownNotes: d.brief.markdownNotes, isActive: true });
  await db.insert(offers).values({
    projectId,
    name: d.offer.name,
    mechanism: d.offer.mechanism,
    desiredAction: d.offer.desiredAction,
    approvedClaimsJson: d.offer.approvedClaims,
    prohibitedClaimsJson: d.offer.prohibitedClaims,
    proofJson: d.offer.proof,
    constraintsJson: d.offer.constraints,
  });
  for (const c of d.cohorts) {
    await db.insert(cohorts).values({
      projectId,
      name: c.name,
      roleIdentity: c.roleIdentity,
      commercialSituation: c.commercialSituation,
      trigger: c.trigger,
      activeProblem: c.activeProblem,
      currentWorkflow: c.currentWorkflow,
      currentBelief: c.currentBelief,
      desiredOutcome: c.desiredOutcome,
      objectionsJson: c.objections,
      decisionCriteriaJson: c.decisionCriteria,
      priority: c.priority,
      offerFit: c.offerFit,
      exclusionCriteriaJson: c.exclusionCriteria,
      exactLanguageJson: c.exactLanguage,
    });
  }

  // Business brief as a crawlable-equivalent source (STRATEGIC_PRIORITY evidence).
  const briefText = [
    d.brief.currentCommercialPriority,
    d.brief.positioning,
    ...d.brief.approvedClaims,
    ...d.brief.availableProof,
  ].join("\n\n");
  await insertSource(db, projectId, {
    ownerType: "BUSINESS_BRIEF",
    competitorSlot: null,
    name: "Business brief",
    url: `https://${d.project.primaryDomain}/__brief`,
    title: "Business brief",
    text: briefText,
  });

  for (const a of d.ownedAssets) await insertSource(db, projectId, a);
  for (const a of d.competitorAssets) await insertSource(db, projectId, a);

  // VoC as a single source; normalization splits into per-row content units.
  const vocText = d.vocRows.map((r) => r.text).join("\n");
  await insertSource(
    db,
    projectId,
    { ownerType: "VOC", competitorSlot: null, name: "Voice of customer", url: `https://${d.project.primaryDomain}/__voc`, title: "VoC", text: vocText },
    "FILE_JSON",
  );

  // Project token for the extension (store hash; return plaintext once).
  const token = `cgi_${randomBytes(24).toString("hex")}`;
  const [tok] = await db.insert(projectTokens).values({ projectId, tokenHash: sha256(token), label: "demo-extension" }).returning({ id: projectTokens.id });

  return { projectId, token, tokenId: tok!.id };
}

async function insertSource(
  db: ReturnType<typeof getDb>,
  projectId: string,
  a: DemoAsset,
  sourceType = "URL",
): Promise<void> {
  const crawlMethod = a.ownerType === "VOC" || sourceType.startsWith("FILE") ? "UPLOAD" : "HTTP";
  const [src] = await db
    .insert(sources)
    .values({
      projectId,
      ownerType: a.ownerType,
      competitorSlot: a.competitorSlot,
      sourceType,
      name: a.name,
      canonicalUrl: a.url,
      crawlMethod,
      status: "PENDING",
    })
    .returning({ id: sources.id });
  await db.insert(sourceSnapshots).values({
    sourceId: src!.id,
    contentHash: contentHash(a.text),
    rawContent: a.text,
    normalizedContent: a.text,
    metadataJson: { title: a.title, publishedAt: a.publishedAt ?? null, competitorSlot: a.competitorSlot },
    isCurrent: true,
  });
  await db.update(sources).set({ status: "PROCESSED", lastSuccessAt: new Date() }).where(eq(sources.id, src!.id));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  seedDemo()
    .then(async (r) => {
      console.log(`Seeded demo project ${r.projectId}`);
      console.log(`Extension project token (save this): ${r.token}`);
      const { closeDb } = await import("./client.js");
      await closeDb();
      process.exit(0);
    })
    .catch((err) => {
      console.error("Seed failed:", err);
      process.exit(1);
    });
}
