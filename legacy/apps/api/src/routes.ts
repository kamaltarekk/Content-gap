import {
  type Db,
  analysisRuns,
  businessBriefs,
  coverageCells,
  cohorts,
  evaluations,
  gapCandidates,
  gapEvidence,
  gaps,
  offers,
  projectTokens,
  projects,
  sources,
  sourceSnapshots,
} from "@cgi/database";
import {
  BusinessBriefSchema,
  CaptureSchema,
  CohortSchema,
  EvaluationSchema,
  OfferSchema,
  ProjectCreateSchema,
  SourceCreateSchema,
  VocRowSchema,
  contentHash,
  sha256,
} from "@cgi/shared";
import { normalizeVocRows, parseCsv } from "@cgi/crawler";
import { ingestContent } from "@cgi/analysis-engine";
import { randomBytes } from "node:crypto";
import { and, desc, eq } from "drizzle-orm";
import type { FastifyInstance } from "fastify";
import { verifyToken } from "./auth.js";
import type { Queue } from "./queue.js";
import { computeCalibration } from "./calibration.js";

export async function registerRoutes(app: FastifyInstance, db: Db, queue: Queue): Promise<void> {
  const requireToken = async (req: { headers: Record<string, unknown> }, projectId: string) => {
    const authed = await verifyToken(db, req.headers.authorization as string | undefined);
    if (!authed || authed.projectId !== projectId) return null;
    return authed;
  };

  app.get("/api/v1/health", async () => ({ status: "ok", pipeline: "v0" }));

  // ---- Projects ----
  app.post("/api/v1/projects", async (req, reply) => {
    const body = ProjectCreateSchema.parse(req.body);
    const [p] = await db.insert(projects).values({
      name: body.name,
      primaryDomain: body.primaryDomain,
      defaultLanguage: body.defaultLanguage,
      refreshSchedule: body.refreshSchedule,
    }).returning();
    return reply.code(201).send(p);
  });

  app.get("/api/v1/projects/:projectId", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const [p] = await db.select().from(projects).where(eq(projects.id, projectId));
    if (!p) return reply.code(404).send({ error: "not_found" });
    return p;
  });

  app.patch("/api/v1/projects/:projectId", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const body = ProjectCreateSchema.partial().parse(req.body);
    const [p] = await db.update(projects).set({ ...body, updatedAt: new Date() }).where(eq(projects.id, projectId)).returning();
    if (!p) return reply.code(404).send({ error: "not_found" });
    return p;
  });

  app.delete("/api/v1/projects/:projectId", async (req) => {
    const { projectId } = req.params as { projectId: string };
    await db.delete(projects).where(eq(projects.id, projectId));
    return { deleted: true };
  });

  // ---- Business brief ----
  app.post("/api/v1/projects/:projectId/business-brief", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const brief = BusinessBriefSchema.parse(req.body);
    await db.update(businessBriefs).set({ isActive: false }).where(eq(businessBriefs.projectId, projectId));
    const [b] = await db.insert(businessBriefs).values({ projectId, structuredDataJson: brief, markdownNotes: brief.markdownNotes, isActive: true }).returning();
    return reply.code(201).send(b);
  });

  app.get("/api/v1/projects/:projectId/business-brief", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const [b] = await db.select().from(businessBriefs).where(and(eq(businessBriefs.projectId, projectId), eq(businessBriefs.isActive, true)));
    if (!b) return reply.code(404).send({ error: "not_found" });
    return b;
  });

  // ---- Offer (single primary offer) ----
  app.post("/api/v1/projects/:projectId/offers", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const o = OfferSchema.parse(req.body);
    const [row] = await db.insert(offers).values({
      projectId, name: o.name, mechanism: o.mechanism, desiredAction: o.desiredAction,
      approvedClaimsJson: o.approvedClaims, prohibitedClaimsJson: o.prohibitedClaims, proofJson: o.proof, constraintsJson: o.constraints,
    }).returning();
    return reply.code(201).send(row);
  });

  // ---- Cohorts ----
  app.post("/api/v1/projects/:projectId/cohorts", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const c = CohortSchema.parse(req.body);
    const [row] = await db.insert(cohorts).values({
      projectId, name: c.name, roleIdentity: c.roleIdentity, commercialSituation: c.commercialSituation, trigger: c.trigger,
      activeProblem: c.activeProblem, currentWorkflow: c.currentWorkflow, currentBelief: c.currentBelief, desiredOutcome: c.desiredOutcome,
      objectionsJson: c.objections, decisionCriteriaJson: c.decisionCriteria, priority: c.priority, offerFit: c.offerFit,
      exclusionCriteriaJson: c.exclusionCriteria, exactLanguageJson: c.exactLanguage,
    }).returning();
    return reply.code(201).send(row);
  });

  app.get("/api/v1/projects/:projectId/cohorts", async (req) => {
    const { projectId } = req.params as { projectId: string };
    return db.select().from(cohorts).where(eq(cohorts.projectId, projectId));
  });

  app.patch("/api/v1/cohorts/:cohortId", async (req, reply) => {
    const { cohortId } = req.params as { cohortId: string };
    const c = CohortSchema.partial().parse(req.body);
    const patch: Record<string, unknown> = { updatedAt: new Date() };
    if (c.name !== undefined) patch.name = c.name;
    if (c.priority !== undefined) patch.priority = c.priority;
    if (c.objections !== undefined) patch.objectionsJson = c.objections;
    if (c.decisionCriteria !== undefined) patch.decisionCriteriaJson = c.decisionCriteria;
    if (c.exactLanguage !== undefined) patch.exactLanguageJson = c.exactLanguage;
    const [row] = await db.update(cohorts).set(patch).where(eq(cohorts.id, cohortId)).returning();
    if (!row) return reply.code(404).send({ error: "not_found" });
    return row;
  });

  // ---- Sources ----
  const triggerAnalysis = async (projectId: string) => queue.enqueueAnalyze({ projectId, triggerType: "INGESTION" });

  app.post("/api/v1/projects/:projectId/sources", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const body = SourceCreateSchema.parse(req.body);
    const [row] = await db.insert(sources).values({
      projectId, ownerType: body.ownerType, competitorSlot: body.competitorSlot, sourceType: body.sourceType,
      name: body.name, canonicalUrl: body.url ?? null, refreshEnabled: body.refreshEnabled,
      crawlMethod: body.sourceType === "URL" || body.sourceType === "SITEMAP" ? "HTTP" : "UPLOAD",
      status: "PENDING",
    }).returning();
    return reply.code(201).send(row);
  });

  app.post("/api/v1/projects/:projectId/sources/upload", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const body = req.body as { ownerType: string; competitorSlot?: number | null; format: string; name: string; content: string };
    if (!body?.content) return reply.code(400).send({ error: "content required" });
    if (body.ownerType === "VOC") {
      let rows: Record<string, unknown>[] = [];
      if (body.format === "csv") rows = parseCsv(body.content);
      else if (body.format === "json") rows = JSON.parse(body.content);
      else rows = body.content.split("\n").filter(Boolean).map((t) => ({ text: t }));
      const { rows: voc, skipped } = normalizeVocRows(rows);
      const text = voc.map((r) => r.text).join("\n");
      const { sourceId, changed } = await ingestContent(db, { projectId, ownerType: "VOC", competitorSlot: null, sourceType: "FILE_" + body.format.toUpperCase(), name: body.name, url: null, title: body.name, text, crawlMethod: "UPLOAD" });
      if (changed) await triggerAnalysis(projectId);
      return reply.code(201).send({ sourceId, importedRows: voc.length, skipped, changed });
    }
    const owner = body.ownerType as "OWNED" | "COMPETITOR";
    const { sourceId, changed } = await ingestContent(db, { projectId, ownerType: owner, competitorSlot: body.competitorSlot ?? null, sourceType: "FILE_" + body.format.toUpperCase(), name: body.name, url: null, title: body.name, text: body.content, crawlMethod: "UPLOAD" });
    if (changed) await triggerAnalysis(projectId);
    return reply.code(201).send({ sourceId, changed });
  });

  // Extension current-page capture (requires project token).
  app.post("/api/v1/projects/:projectId/sources/capture", async (req, reply) => {
    const { projectId } = req.params as { projectId: string };
    const authed = await requireToken(req, projectId);
    if (!authed) return reply.code(401).send({ error: "invalid_token" });
    const cap = CaptureSchema.parse(req.body);
    const { sourceId, changed } = await ingestContent(db, {
      projectId, ownerType: cap.ownerType, competitorSlot: cap.competitorSlot, sourceType: "CAPTURE",
      name: cap.title || cap.url, url: cap.url, title: cap.title, text: cap.text, crawlMethod: "CAPTURE",
    });
    if (changed) await triggerAnalysis(projectId);
    return reply.code(201).send({ sourceId, changed, titleLength: cap.title.length, textLength: cap.text.length });
  });

  app.get("/api/v1/projects/:projectId/sources", async (req) => {
    const { projectId } = req.params as { projectId: string };
    const rows = await db.select().from(sources).where(eq(sources.projectId, projectId));
    return {
      pending: rows.filter((r) => r.status === "PENDING" || r.status === "PROCESSING"),
      processed: rows.filter((r) => r.status === "PROCESSED"),
      failed: rows.filter((r) => r.status === "FAILED"),
      needsAttention: rows.filter((r) => r.status === "NEEDS_ATTENTION"),
      all: rows,
    };
  });

  app.get("/api/v1/sources/:sourceId", async (req, reply) => {
    const { sourceId } = req.params as { sourceId: string };
    const [s] = await db.select().from(sources).where(eq(sources.id, sourceId));
    if (!s) return reply.code(404).send({ error: "not_found" });
    const snaps = await db.select().from(sourceSnapshots).where(eq(sourceSnapshots.sourceId, sourceId));
    return { source: s, snapshots: snaps };
  });

  app.delete("/api/v1/sources/:sourceId", async (req) => {
    const { sourceId } = req.params as { sourceId: string };
    await db.delete(sources).where(eq(sources.id, sourceId));
    return { deleted: true };
  });

  // ---- Runs ----
  app.get("/api/v1/projects/:projectId/runs", async (req) => {
    const { projectId } = req.params as { projectId: string };
    return db.select().from(analysisRuns).where(eq(analysisRuns.projectId, projectId)).orderBy(desc(analysisRuns.createdAt)).limit(50);
  });
  app.get("/api/v1/runs/:runId", async (req, reply) => {
    const { runId } = req.params as { runId: string };
    const [r] = await db.select().from(analysisRuns).where(eq(analysisRuns.id, runId));
    if (!r) return reply.code(404).send({ error: "not_found" });
    return r;
  });

  // ---- Gaps ----
  app.get("/api/v1/projects/:projectId/gaps", async (req) => {
    const { projectId } = req.params as { projectId: string };
    const q = req.query as { cohortId?: string; journeyStage?: string };
    let rows = await db.select().from(gaps).where(and(eq(gaps.projectId, projectId), eq(gaps.status, "PUBLISHED")));
    if (q.cohortId) rows = rows.filter((r) => r.cohortId === q.cohortId);
    if (q.journeyStage) rows = rows.filter((r) => r.journeyStage === q.journeyStage);
    rows.sort((a, b) => b.priorityScore - a.priorityScore);
    return rows;
  });

  app.get("/api/v1/gaps/:gapId", async (req, reply) => {
    const { gapId } = req.params as { gapId: string };
    const [g] = await db.select().from(gaps).where(eq(gaps.id, gapId));
    if (!g) return reply.code(404).send({ error: "not_found" });
    const ev = await db.select().from(gapEvidence).where(eq(gapEvidence.gapId, gapId));
    return { ...g, evidence: ev };
  });

  // ---- Coverage matrix ----
  app.get("/api/v1/projects/:projectId/coverage", async (req) => {
    const { projectId } = req.params as { projectId: string };
    const cells = await db.select().from(coverageCells).where(eq(coverageCells.projectId, projectId));
    const publishedGaps = await db.select().from(gaps).where(and(eq(gaps.projectId, projectId), eq(gaps.status, "PUBLISHED")));
    interface Cell { requiredNeeds: number; strong: number; weakOrPartial: number; gaps: number; evidenceGaps: number; oversaturated: number }
    const newCell = (): Cell => ({ requiredNeeds: 0, strong: 0, weakOrPartial: 0, gaps: 0, evidenceGaps: 0, oversaturated: 0 });
    const matrix = new Map<string, Cell>();
    for (const c of cells) {
      const key = `${c.cohortId}|${c.journeyStage}`;
      const cur = matrix.get(key) ?? newCell();
      cur.requiredNeeds += 1;
      if (c.coverageStatus === "STRONG") cur.strong += 1;
      if (["WEAK", "PARTIAL", "MENTION_ONLY"].includes(c.coverageStatus)) cur.weakOrPartial += 1;
      if (c.coverageStatus === "UNSUPPORTED") cur.evidenceGaps += 1;
      if (c.coverageStatus === "OVERSATURATED") cur.oversaturated += 1;
      matrix.set(key, cur);
    }
    for (const g of publishedGaps) {
      const key = `${g.cohortId}|${g.journeyStage}`;
      const cur = matrix.get(key) ?? newCell();
      cur.gaps += 1;
      matrix.set(key, cur);
    }
    return { cells, matrix: [...matrix.entries()].map(([k, v]) => ({ cohortId: k.split("|")[0], journeyStage: k.split("|")[1], ...v })) };
  });

  // ---- Evaluations + shadow sample + calibration ----
  app.post("/api/v1/gaps/:gapId/evaluations", async (req, reply) => {
    const { gapId } = req.params as { gapId: string };
    const body = EvaluationSchema.parse(req.body);
    const [row] = await db.insert(evaluations).values({
      gapId, evaluatorName: body.evaluatorName, validityRating: body.validityRating, commercialRelevanceRating: body.commercialRelevanceRating,
      noveltyRating: body.noveltyRating, evidenceQualityRating: body.evidenceQualityRating, actionabilityRating: body.actionabilityRating,
      acceptedIntoPlan: body.acceptedIntoPlan, markedMissedValidGap: body.markedMissedValidGap, notes: body.notes,
    }).returning();
    return reply.code(201).send(row);
  });

  app.post("/api/v1/candidates/:candidateId/evaluations", async (req, reply) => {
    const { candidateId } = req.params as { candidateId: string };
    const body = EvaluationSchema.parse(req.body);
    const [row] = await db.insert(evaluations).values({
      gapCandidateId: candidateId, evaluatorName: body.evaluatorName, validityRating: body.validityRating,
      commercialRelevanceRating: body.commercialRelevanceRating, noveltyRating: body.noveltyRating,
      evidenceQualityRating: body.evidenceQualityRating, actionabilityRating: body.actionabilityRating,
      acceptedIntoPlan: body.acceptedIntoPlan, markedMissedValidGap: body.markedMissedValidGap, notes: body.notes,
    }).returning();
    return reply.code(201).send(row);
  });

  app.get("/api/v1/projects/:projectId/evaluations", async (req) => {
    const { projectId } = req.params as { projectId: string };
    const projGaps = await db.select().from(gaps).where(eq(gaps.projectId, projectId));
    const gapIds = new Set(projGaps.map((g) => g.id));
    const allEvals = await db.select().from(evaluations);
    const relevant = allEvals.filter((e) => (e.gapId && gapIds.has(e.gapId)));
    return { evaluations: relevant, calibration: computeCalibration(projGaps, relevant) };
  });

  app.get("/api/v1/projects/:projectId/shadow-sample", async (req) => {
    const { projectId } = req.params as { projectId: string };
    // Do not reveal original rank until after evaluation.
    const rows = await db.select().from(gapCandidates).where(and(eq(gapCandidates.projectId, projectId), eq(gapCandidates.isShadowSample, true)));
    return rows.map((r) => ({ id: r.id, cohortId: r.cohortId, journeyStage: r.journeyStage, gapType: r.gapType, title: r.title, rejectionReason: r.rejectionReason }));
  });

  // ---- Tokens ----
  app.post("/api/v1/tokens", async (req, reply) => {
    const body = req.body as { projectId: string; label: string };
    if (!body?.projectId || !body?.label) return reply.code(400).send({ error: "projectId and label required" });
    const token = `cgi_${randomBytes(24).toString("hex")}`;
    const [row] = await db.insert(projectTokens).values({ projectId: body.projectId, tokenHash: sha256(token), label: body.label }).returning({ id: projectTokens.id });
    return reply.code(201).send({ id: row!.id, token, note: "Store this token now — it is not retrievable later." });
  });

  app.delete("/api/v1/tokens/:tokenId", async (req) => {
    const { tokenId } = req.params as { tokenId: string };
    await db.delete(projectTokens).where(eq(projectTokens.id, tokenId));
    return { deleted: true };
  });

  // Connection test for the extension.
  app.get("/api/v1/me", async (req, reply) => {
    const authed = await verifyToken(db, req.headers.authorization as string | undefined);
    if (!authed) return reply.code(401).send({ error: "invalid_token" });
    const [p] = await db.select().from(projects).where(eq(projects.id, authed.projectId));
    return { projectId: authed.projectId, projectName: p?.name ?? null };
  });

  void contentHash;
}
