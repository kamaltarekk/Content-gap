import type { EmbeddingProvider, LlmProvider } from "@cgi/llm";
import { detectInjection } from "@cgi/llm";
import {
  type Db,
  analysisRuns,
  chunks as chunksTable,
  coverageCells,
  contentUnits,
  cohorts as cohortsTable,
  decisionNeeds,
  extractedSignals,
  gapCandidates,
  gapEvidence,
  gaps as gapsTable,
  sources as sourcesTable,
  sourceSnapshots,
  usageEvents,
} from "@cgi/database";
import {
  type AppConfig,
  type RankingComponents,
  PIPELINE_VERSION,
  classifyEvidenceStatus,
  contentHash,
  estimateCostUsd,
  isOlderThan,
  loadConfig,
} from "@cgi/shared";
import { detectLanguage, matchCohort } from "@cgi/llm";
import { and, eq, inArray, sql } from "drizzle-orm";
import { logger, type StageLogEntry } from "./logger.js";
import { prioritize } from "./prioritize.js";
import { Retriever, keywordOverlap } from "./retrieval.js";
import { offsetsValid, verifyQuote } from "./verify-evidence.js";
import { selectShadowSample } from "./shadow-sample.js";

export interface RunDeps {
  db: Db;
  llm: LlmProvider;
  embed: EmbeddingProvider;
  config?: AppConfig;
  /** Reference date (ISO) for deterministic "outdated" checks. Defaults to today. */
  referenceDate?: string;
  /** Optional fetcher for URL sources; omitted in offline demo/tests. */
  refetchUrlSources?: boolean;
}

interface UsageAccumulator {
  inputTokens: number;
  outputTokens: number;
  calls: number;
  suspicious: string[];
}

const CHUNK_CHARS = 1200;

export async function runPipeline(
  projectId: string,
  triggerType: "INGESTION" | "WEEKLY_REFRESH" | "MANUAL_SETUP" | "TEST",
  deps: RunDeps,
): Promise<{ runId: string; publishedGapIds: string[]; status: string }> {
  const config = deps.config ?? loadConfig();
  const { db, llm, embed } = deps;
  const referenceDate = deps.referenceDate ?? new Date().toISOString().slice(0, 10);
  const stageLog: StageLogEntry[] = [];
  const usage: UsageAccumulator = { inputTokens: 0, outputTokens: 0, calls: 0, suspicious: [] };

  const [run] = await db
    .insert(analysisRuns)
    .values({ projectId, triggerType, status: "RUNNING", pipelineVersion: PIPELINE_VERSION, startedAt: new Date() })
    .returning();
  const runId = run!.id;
  const log = logger.child({ runId, projectId });

  const stage = async <T>(name: string, fn: () => Promise<{ inputCount: number; outputCount: number; result: T; note?: string }>): Promise<T> => {
    const start = Date.now();
    try {
      const { inputCount, outputCount, result, note } = await fn();
      stageLog.push({ stage: name, pipelineVersion: PIPELINE_VERSION, status: "ok", inputCount, outputCount, ms: Date.now() - start, note });
      log.info({ stage: name, inputCount, outputCount }, "stage ok");
      return result;
    } catch (err) {
      stageLog.push({ stage: name, pipelineVersion: PIPELINE_VERSION, status: "failed", inputCount: 0, outputCount: 0, ms: Date.now() - start, error: (err as Error).message });
      log.error({ stage: name, err: (err as Error).message }, "stage failed");
      throw err;
    }
  };

  const recordUsage = async (operation: string, u: { usage: { inputTokens: number; outputTokens: number }; suspiciousInstructions: string[] }) => {
    usage.inputTokens += u.usage.inputTokens;
    usage.outputTokens += u.usage.outputTokens;
    usage.calls += 1;
    if (u.suspiciousInstructions.length) {
      usage.suspicious.push(...u.suspiciousInstructions);
      log.warn({ operation, suspicious: u.suspiciousInstructions }, "ignored instruction-like source content (treated as data only)");
    }
    await db.insert(usageEvents).values({
      projectId,
      runId,
      provider: llm.name,
      model: llm.model,
      operation,
      inputTokens: u.usage.inputTokens,
      outputTokens: u.usage.outputTokens,
      estimatedCost: String(estimateCostUsd(u.usage.inputTokens, u.usage.outputTokens, config.pricing)),
    });
  };

  let status: "SUCCEEDED" | "PARTIAL" | "FAILED" = "SUCCEEDED";
  const publishedGapIds: string[] = [];

  try {
    // ---- Load setup ----
    const cohortRows = await db.select().from(cohortsTable).where(eq(cohortsTable.projectId, projectId));
    const cohortKeywords = cohortRows.map((c) => ({
      id: c.id,
      keywords: [...(c.exactLanguageJson as string[]), c.name],
    }));
    const allSources = await db.select().from(sourcesTable).where(eq(sourcesTable.projectId, projectId));
    const sourceById = new Map(allSources.map((s) => [s.id, s]));

    // ---- Stage: Ingestion (hash-gated; ensure current snapshots exist) ----
    const snapshotsToProcess = await stage("ingestion", async () => {
      const snaps = await db
        .select({ snap: sourceSnapshots, ownerType: sourcesTable.ownerType })
        .from(sourceSnapshots)
        .innerJoin(sourcesTable, eq(sourceSnapshots.sourceId, sourcesTable.id))
        .where(and(eq(sourcesTable.projectId, projectId), eq(sourceSnapshots.isCurrent, true)));
      // Only process snapshots that have no content units yet (idempotent / targeted reprocessing).
      const process: typeof snaps = [];
      for (const s of snaps) {
        const existing = await db.select({ id: contentUnits.id }).from(contentUnits).where(eq(contentUnits.sourceSnapshotId, s.snap.id)).limit(1);
        if (existing.length === 0) process.push(s);
      }
      return { inputCount: snaps.length, outputCount: process.length, result: process };
    });

    // ---- Stage: Normalization (snapshot -> content units) ----
    const newUnitIds = await stage("normalization", async () => {
      const created: string[] = [];
      for (const { snap, ownerType } of snapshotsToProcess) {
        const meta = (snap.metadataJson as Record<string, unknown>) ?? {};
        const source = sourceById.get(snap.sourceId);
        if (ownerType === "VOC") {
          const rows = snap.normalizedContent.split("\n").map((r) => r.trim()).filter(Boolean);
          for (const row of rows) {
            const [cu] = await db
              .insert(contentUnits)
              .values({ projectId, sourceSnapshotId: snap.id, title: "", body: row, language: detectLanguage(row), assetType: "SOCIAL_POST", url: source?.canonicalUrl ?? null, metadataJson: { ownerType } })
              .returning({ id: contentUnits.id });
            created.push(cu!.id);
          }
        } else {
          const [cu] = await db
            .insert(contentUnits)
            .values({
              projectId,
              sourceSnapshotId: snap.id,
              title: (meta.title as string) ?? source?.name ?? "",
              body: snap.normalizedContent,
              language: detectLanguage(snap.normalizedContent),
              publishedAt: (meta.publishedAt as string) ?? null,
              assetType: "ARTICLE",
              url: source?.canonicalUrl ?? null,
              metadataJson: { ownerType, competitorSlot: source?.competitorSlot ?? null },
            })
            .returning({ id: contentUnits.id });
          created.push(cu!.id);
        }
      }
      return { inputCount: snapshotsToProcess.length, outputCount: created.length, result: created };
    });

    // ---- Stage: Chunking + embeddings ----
    await stage("chunking", async () => {
      let chunkCount = 0;
      for (const unitId of newUnitIds) {
        const [unit] = await db.select().from(contentUnits).where(eq(contentUnits.id, unitId));
        if (!unit) continue;
        const pieces = chunkText(unit.body);
        if (chunkCount + pieces.length > config.limits.maxChunksPerRun) {
          throw new Error(`maxChunksPerRun (${config.limits.maxChunksPerRun}) exceeded`);
        }
        const vectors = await embed.embed(pieces.map((p) => p.text));
        for (let i = 0; i < pieces.length; i++) {
          await db.insert(chunksTable).values({
            contentUnitId: unitId,
            chunkIndex: i,
            text: pieces[i]!.text,
            startOffset: pieces[i]!.start,
            endOffset: pieces[i]!.end,
            embedding: vectors[i]!,
            tokenCount: Math.ceil(pieces[i]!.text.length / 4),
          });
          chunkCount++;
        }
      }
      return { inputCount: newUnitIds.length, outputCount: chunkCount, result: null };
    });

    // ---- Stage: Structured Extraction (LLM) ----
    await stage("extraction", async () => {
      let signalCount = 0;
      for (const unitId of newUnitIds) {
        const [unit] = await db.select().from(contentUnits).where(eq(contentUnits.id, unitId));
        if (!unit) continue;
        const ownerType = ((unit.metadataJson as Record<string, unknown>).ownerType as string) ?? "OWNED";
        const unitChunks = await db.select().from(chunksTable).where(eq(chunksTable.contentUnitId, unitId));
        const res = await llm.extract({
          contentUnit: { id: unit.id, title: unit.title, body: unit.body, language: unit.language, ownerType },
          chunks: unitChunks.map((c) => ({ id: c.id, text: c.text })),
          cohorts: cohortKeywords.map((c) => ({ id: c.id, name: cohortRows.find((r) => r.id === c.id)!.name, keywords: c.keywords })),
        });
        await recordUsage("extraction", res);
        for (const s of res.data.signals) {
          await db.insert(extractedSignals).values({
            projectId,
            contentUnitId: unit.id,
            chunkId: s.evidenceChunkId,
            signalType: s.type,
            normalizedLabel: s.normalizedLabel,
            rawText: s.rawText,
            cohortId: s.cohortId,
            journeyStage: s.journeyStage,
            evidenceWeight: ownerType === "VOC" || ownerType === "BUSINESS_BRIEF" ? 2 : 1,
          });
          signalCount++;
        }
      }
      return { inputCount: newUnitIds.length, outputCount: signalCount, result: null };
    });

    // ---- Load full corpus (this project) for downstream stages ----
    const allUnits = await db.select().from(contentUnits).where(eq(contentUnits.projectId, projectId));
    const allChunks = await db.select().from(chunksTable);
    const chunkById = new Map(allChunks.map((c) => [c.id, c]));
    const unitOwner = (u: (typeof allUnits)[number]) => ((u.metadataJson as Record<string, unknown>).ownerType as string) ?? "OWNED";
    const chunksByUnit = new Map<string, typeof allChunks>();
    for (const c of allChunks) {
      const arr = chunksByUnit.get(c.contentUnitId) ?? [];
      arr.push(c);
      chunksByUnit.set(c.contentUnitId, arr);
    }
    const ownerOfChunk = (chunkId: string): string => {
      const ch = chunkById.get(chunkId);
      if (!ch) return "OWNED";
      const unit = allUnits.find((u) => u.id === ch.contentUnitId);
      return unit ? unitOwner(unit) : "OWNED";
    };

    // Index embeddings for retrieval (deterministic, in-memory).
    const retriever = new Retriever(embed);
    await retriever.index(allChunks.map((c) => ({ id: c.id, text: c.text })));
    await retriever.index(allUnits.map((u) => ({ id: `unit:${u.id}`, text: `${u.title}\n${u.body}` })));

    // ---- Stage: Semantic Deduplication (collapse duplicate extracted signals) ----
    await stage("semantic-dedup", async () => {
      const sigs = await db.select().from(extractedSignals).where(eq(extractedSignals.projectId, projectId));
      const seen = new Set<string>();
      let removed = 0;
      for (const s of sigs) {
        const key = `${s.signalType}|${s.cohortId ?? "none"}|${s.normalizedLabel.toLowerCase()}`;
        if (seen.has(key)) {
          await db.delete(extractedSignals).where(eq(extractedSignals.id, s.id));
          removed++;
        } else seen.add(key);
      }
      return { inputCount: sigs.length, outputCount: sigs.length - removed, result: null, note: `${removed} duplicate signals collapsed` };
    });

    // ---- Stage: Required Decision-Support Map (LLM, brief/cohort/VoC only) ----
    const needRows = await stage("decision-support-map", async () => {
      // Clear prior needs for a clean recompute.
      await db.delete(decisionNeeds).where(eq(decisionNeeds.projectId, projectId));
      const vocChunks = allChunks.filter((c) => ownerOfChunk(c.id) === "VOC");
      const briefChunks = allChunks.filter((c) => ownerOfChunk(c.id) === "BUSINESS_BRIEF");
      const vocSignals = vocChunks.map((c) => ({ chunkId: c.id, text: c.text, cohortId: matchCohort(c.text, cohortKeywords) }));
      const res = await llm.mapDecisionSupport({
        cohorts: cohortRows.map((c) => ({
          id: c.id,
          name: c.name,
          keywords: cohortKeywords.find((k) => k.id === c.id)!.keywords,
          objections: c.objectionsJson as string[],
          decisionCriteria: c.decisionCriteriaJson as string[],
          activeProblem: c.activeProblem,
          currentBelief: c.currentBelief,
          desiredOutcome: c.desiredOutcome,
        })),
        brief: { approvedProof: [], commercialPriority: "" },
        vocSignals,
      });
      await recordUsage("decision-support", res);
      const inserted: { id: string; cohortId: string; journeyStage: string; needType: string; normalizedNeed: string; supportingChunkIds: string[] }[] = [];
      for (const need of res.data.needs) {
        // Attach demand evidence: VoC + brief chunks overlapping this need (semantic + keyword gate).
        const pool = [...vocChunks, ...briefChunks].map((c) => c.id);
        const shortlisted = await retriever.topK(need.normalizedNeed, pool, 6);
        const demand = shortlisted
          .map((s) => s.id)
          .filter((id) => keywordOverlap(chunkById.get(id)!.text, need.normalizedNeed) || need.supportingChunkIds.includes(id));
        const evidenceIds = demand.length ? demand : need.supportingChunkIds;
        const [row] = await db
          .insert(decisionNeeds)
          .values({ projectId, cohortId: need.cohortId, journeyStage: need.journeyStage, needType: need.needType, normalizedNeed: need.normalizedNeed, description: need.description, evidenceJson: evidenceIds })
          .returning({ id: decisionNeeds.id });
        inserted.push({ id: row!.id, cohortId: need.cohortId, journeyStage: need.journeyStage, needType: need.needType, normalizedNeed: need.normalizedNeed, supportingChunkIds: evidenceIds });
      }
      return { inputCount: cohortRows.length, outputCount: inserted.length, result: inserted };
    });

    // Resolve a candidate back to its need id via (cohortId | normalizedNeed). The fake/real
    // providers set customerQuestionOrBelief = need.normalizedNeed, so this is stable.
    const needIdByKey = new Map(needRows.map((n) => [`${n.cohortId}|${n.normalizedNeed}`, n.id]));

    // ---- Stage: Current Coverage Matrix (retrieval shortlist -> LLM classify) ----
    const coverageByNeedKey = await stage("coverage-matrix", async () => {
      await db.delete(coverageCells).where(eq(coverageCells.projectId, projectId));
      const ownedUnits = allUnits.filter((u) => unitOwner(u) === "OWNED");
      const ownedUnitIds = ownedUnits.map((u) => `unit:${u.id}`);
      const signalsByUnit = new Map<string, string[]>();
      const allSignals = await db.select().from(extractedSignals).where(eq(extractedSignals.projectId, projectId));
      for (const s of allSignals) {
        const arr = signalsByUnit.get(s.contentUnitId) ?? [];
        arr.push(s.signalType);
        signalsByUnit.set(s.contentUnitId, arr);
      }
      const needKey = (n: { id: string }) => n.id;
      const coverageInputNeeds = needRows.map((n) => ({ needKey: needKey(n), cohortId: n.cohortId, journeyStage: n.journeyStage as never, normalizedNeed: n.normalizedNeed, description: "" }));

      // Shortlist owned units per need.
      const shortlistUnitIds = new Set<string>();
      const matchedByNeed = new Map<string, Set<string>>();
      for (const n of needRows) {
        const top = await retriever.topK(n.normalizedNeed, ownedUnitIds, 4);
        const matched = new Set<string>();
        for (const t of top) {
          const realId = t.id.replace("unit:", "");
          const unit = ownedUnits.find((u) => u.id === realId)!;
          if (keywordOverlap(`${unit.title}\n${unit.body}`, n.normalizedNeed)) {
            matched.add(realId);
            shortlistUnitIds.add(realId);
          }
        }
        matchedByNeed.set(n.id, matched);
      }

      const shortlisted = ownedUnits.filter((u) => shortlistUnitIds.has(u.id));
      const ownedUnitsInput = shortlisted.map((u) => {
        const types = signalsByUnit.get(u.id) ?? [];
        const matchedNeedKeys = needRows.filter((n) => matchedByNeed.get(n.id)?.has(u.id)).map((n) => n.id);
        return {
          id: u.id,
          title: u.title,
          text: u.body,
          hasProofSignal: types.includes("PROOF"),
          connectsToOffer: /offer|book|demo|trial|pricing|احجز|تواصل|عرض/i.test(u.body) || types.includes("CTA"),
          hasCta: types.includes("CTA"),
          isOutdated: isOlderThan(u.publishedAt, 365 * 2, referenceDate),
          hasUnsupportedClaim: types.includes("CLAIM") && !types.includes("PROOF"),
          matchedNeedKeys,
        };
      });

      const res = await llm.classifyCoverage({ needs: coverageInputNeeds, ownedUnits: ownedUnitsInput });
      await recordUsage("coverage", res);
      const map = new Map<string, { status: string; unitIds: string[]; summary: string; hasProof: boolean }>();
      for (const c of res.data.classifications) {
        const need = needRows.find((n) => n.id === c.needKey);
        if (!need) continue;
        await db.insert(coverageCells).values({
          projectId,
          cohortId: need.cohortId,
          journeyStage: need.journeyStage,
          needType: need.needType,
          normalizedNeed: need.normalizedNeed,
          coverageStatus: c.coverageStatus,
          coverageStrength: coverageStrengthOf(c.coverageStatus),
          supportingAssetCount: c.matchedContentUnitIds.length,
          effectiveAssetCount: c.hasProof ? c.matchedContentUnitIds.length : 0,
          evidenceJson: c.matchedContentUnitIds,
        });
        map.set(c.needKey, { status: c.coverageStatus, unitIds: c.matchedContentUnitIds, summary: c.summary, hasProof: c.hasProof });
      }
      return { inputCount: needRows.length, outputCount: map.size, result: map };
    });

    // ---- Stage: Candidate Gap Generation (LLM) ----
    const candidateIds = await stage("candidate-generation", async () => {
      await db.delete(gapCandidates).where(and(eq(gapCandidates.projectId, projectId), eq(gapCandidates.runId, runId)));
      const evidenceChunkPool = new Map<string, { id: string; text: string; ownerType: string }>();
      const candNeeds = needRows.map((n) => {
        const cov = coverageByNeedKey.get(n.id);
        for (const cid of n.supportingChunkIds) {
          const ch = chunkById.get(cid);
          if (ch) evidenceChunkPool.set(cid, { id: cid, text: ch.text, ownerType: ownerOfChunk(cid) });
        }
        return {
          needKey: n.id,
          cohortId: n.cohortId,
          journeyStage: n.journeyStage as never,
          normalizedNeed: n.normalizedNeed,
          needType: n.needType,
          coverageStatus: cov?.status ?? "NONE",
          demandChunkIds: n.supportingChunkIds,
          coverageUnitIds: cov?.unitIds ?? [],
        };
      });
      const res = await llm.generateCandidates({
        cohorts: cohortRows.map((c) => ({ id: c.id, name: c.name, priority: c.priority })),
        needs: candNeeds,
        chunks: [...evidenceChunkPool.values()],
      });
      await recordUsage("candidate-generation", res);
      const ids: string[] = [];
      for (const c of res.data.candidates) {
        const [row] = await db
          .insert(gapCandidates)
          .values({ projectId, runId, cohortId: c.cohortId, journeyStage: c.journeyStage, gapType: c.gapType, title: c.title, candidateDataJson: c, generationReason: c.generationReason, status: "CANDIDATE" })
          .returning({ id: gapCandidates.id });
        ids.push(row!.id);
      }
      return { inputCount: candNeeds.length, outputCount: ids.length, result: ids };
    });

    // ---- Stage: Evidence Verification (DETERMINISTIC) + Critique + Prioritization ----
    interface Verified {
      candidateId: string;
      data: import("@cgi/shared").CandidateGap;
      evidence: { role: string; chunkId: string; quote: string; start: number; end: number }[];
      evidenceStatus: string;
      evidenceStatusRule: string;
      coverageStatus: string;
      coverageSummary: string;
      score: number;
      label: string;
      rejected: boolean;
      rejectionReason: string | null;
    }

    const verified = await stage("evidence-verification", async () => {
      const out: Verified[] = [];
      for (const candidateId of candidateIds) {
        const [cand] = await db.select().from(gapCandidates).where(eq(gapCandidates.id, candidateId));
        if (!cand) continue;
        const data = cand.candidateDataJson as import("@cgi/shared").CandidateGap;
        const evidence: Verified["evidence"] = [];
        for (const ev of data.evidence) {
          const chunk = chunkById.get(ev.chunkId);
          if (!chunk) continue; // unknown id already blocked upstream; belt-and-suspenders
          const v = verifyQuote(chunk.text, ev.exactQuote);
          if (v.verified && offsetsValid(chunk.text, v.startOffset, v.endOffset)) {
            evidence.push({ role: ev.role, chunkId: ev.chunkId, quote: chunk.text.slice(v.startOffset, v.endOffset), start: v.startOffset, end: v.endOffset });
          }
        }
        const needId = needIdByKey.get(`${data.cohortId}|${data.customerQuestionOrBelief}`);
        const cov = (needId ? coverageByNeedKey.get(needId) : undefined) ?? { status: "NONE" as const, summary: "", unitIds: [], hasProof: false };
        const coverageStatus = cov.status;
        const evForStatus = evidence.map((e) => ({ role: e.role as never, ownerType: ownerOfChunk(e.chunkId) as never, verified: true }));
        const statusResult = classifyEvidenceStatus(evForStatus, coverageStatus as never);
        out.push({
          candidateId,
          data,
          evidence,
          evidenceStatus: statusResult.status,
          evidenceStatusRule: `${statusResult.ruleId}: ${statusResult.explanation}`,
          coverageStatus,
          coverageSummary: cov.summary || `Coverage: ${coverageStatus}`,
          score: 0,
          label: "P5_REJECT",
          rejected: false,
          rejectionReason: null,
        });
      }
      return { inputCount: candidateIds.length, outputCount: out.length, result: out };
    });

    await stage("critique-rejection", async () => {
      const titlesSeen = new Map<string, string>();
      let rejected = 0;
      for (const v of verified) {
        const hasCustomerDemand = v.evidence.some((e) => ownerOfChunk(e.chunkId) === "VOC" || e.role === "CUSTOMER_DEMAND");
        const dupTitle = [...titlesSeen.keys()].find((t) => titleSimilar(t, v.data.title)) ?? null;
        const res = await llm.critique({
          candidate: {
            title: v.data.title,
            gapType: v.data.gapType,
            cohortId: v.data.cohortId,
            coverageStatus: v.coverageStatus,
            hasVerifiedCustomerDemand: hasCustomerDemand,
            hasVerifiedOwnedCoverageAlready: v.coverageStatus === "STRONG",
            isDuplicateOfTitle: dupTitle,
            looksLikeNonContentProblem: /support|billing|refund|دعم|فاتورة/i.test(v.data.title),
          },
        });
        await recordUsage("critique", res);
        const action = res.data.action;
        if (action === "REJECT" || action === "MARK_NON_CONTENT" || action === "MERGE") {
          v.rejected = true;
          v.rejectionReason = `${action}: ${res.data.reason}`;
          rejected++;
        } else {
          if (action === "DOWNGRADE") v.evidenceStatus = "HYPOTHESIS";
          titlesSeen.set(v.data.title, v.candidateId);
        }
        // Deterministic prioritization from stored components.
        const components = v.data.rankingComponents as RankingComponents;
        const pr = prioritize(components, v.rejected);
        v.score = pr.score;
        v.label = pr.label;
        await db.update(gapCandidates).set({ status: v.rejected ? "REJECTED" : "VERIFIED", rejectionReason: v.rejectionReason, priorityScore: v.score, priorityLabel: v.label }).where(eq(gapCandidates.id, v.candidateId));
      }
      return { inputCount: verified.length, outputCount: verified.length - rejected, result: null };
    });

    // ---- Stage: Transparent Prioritization + Publication (cap 10) + Shadow sample ----
    await stage("publication", async () => {
      const survivors = verified.filter((v) => !v.rejected && v.label !== "P5_REJECT").sort((a, b) => b.score - a.score);
      const published = survivors.slice(0, config.limits.maxPublishedGaps);
      const notPublished = verified.filter((v) => !published.includes(v));

      for (const v of published) {
        const cohort = cohortRows.find((c) => c.id === v.data.cohortId);
        const [gap] = await db
          .insert(gapsTable)
          .values({
            projectId,
            gapCandidateId: v.candidateId,
            runId,
            cohortId: v.data.cohortId,
            journeyStage: v.data.journeyStage,
            gapType: v.data.gapType,
            title: v.data.title,
            customerNeed: v.data.customerQuestionOrBelief,
            currentCoverageSummary: v.coverageSummary,
            missingDecisionSupport: v.data.missingDecisionSupport,
            commercialConsequence: v.data.commercialConsequence,
            recommendedContentRole: v.data.recommendedContentRole,
            recommendedAssetType: v.data.recommendedAssetType,
            suggestedTouchpoint: v.data.suggestedTouchpoint,
            evidenceStatus: v.evidenceStatus,
            evidenceStatusRule: v.evidenceStatusRule,
            priorityLabel: v.label,
            priorityScore: v.score,
            rankingComponentsJson: v.data.rankingComponents,
            rankingReason: v.data.generationReason,
            status: "PUBLISHED",
          })
          .returning({ id: gapsTable.id });
        publishedGapIds.push(gap!.id);
        await db.update(gapCandidates).set({ status: "PUBLISHED" }).where(eq(gapCandidates.id, v.candidateId));
        for (const e of v.evidence) {
          const chunk = chunkById.get(e.chunkId)!;
          const unit = allUnits.find((u) => u.id === chunk.contentUnitId)!;
          const [snap] = await db.select().from(sourceSnapshots).where(eq(sourceSnapshots.id, unit.sourceSnapshotId));
          await db.insert(gapEvidence).values({
            gapId: gap!.id,
            sourceId: snap?.sourceId ?? null,
            sourceSnapshotId: unit.sourceSnapshotId,
            contentUnitId: unit.id,
            chunkId: e.chunkId,
            evidenceRole: e.role,
            exactQuote: e.quote,
            quoteStartOffset: e.start,
            quoteEndOffset: e.end,
          });
        }
        void cohort;
      }

      // Shadow sample from rejected + not-published survivors.
      const shadowPool = notPublished.map((v) => ({ id: v.candidateId }));
      const shadow = selectShadowSample(shadowPool, runId);
      const shadowIds = new Set(shadow.map((s) => s.id));
      if (shadowIds.size) {
        await db.update(gapCandidates).set({ isShadowSample: true, status: "SHADOW" }).where(inArray(gapCandidates.id, [...shadowIds]));
      }
      return { inputCount: verified.length, outputCount: published.length, result: null, note: `${shadowIds.size} shadow candidates` };
    });

    if (usage.calls === 0) status = "PARTIAL";
  } catch (err) {
    status = "FAILED";
    await db.update(analysisRuns).set({ status, completedAt: new Date(), errorSummary: (err as Error).message, stageLogJson: stageLog }).where(eq(analysisRuns.id, runId));
    logger.error({ runId, err: (err as Error).message }, "pipeline failed");
    return { runId, publishedGapIds, status };
  }

  const cost = estimateCostUsd(usage.inputTokens, usage.outputTokens, config.pricing);
  await db
    .update(analysisRuns)
    .set({
      status,
      completedAt: new Date(),
      stageLogJson: stageLog,
      inputCountsJson: { sources: 0 },
      outputCountsJson: { publishedGaps: publishedGapIds.length },
      usageJson: {
        provider: llm.name,
        model: llm.model,
        llmCalls: usage.calls,
        inputTokens: usage.inputTokens,
        outputTokens: usage.outputTokens,
        estimatedCostUsd: cost,
        costPerPublishedGap: publishedGapIds.length ? Math.round((cost / publishedGapIds.length) * 1e6) / 1e6 : 0,
        ignoredInjectionAttempts: usage.suspicious.length,
      },
    })
    .where(eq(analysisRuns.id, runId));

  return { runId, publishedGapIds, status };
}

// ---- helpers ----

function chunkText(body: string): { text: string; start: number; end: number }[] {
  if (body.length <= CHUNK_CHARS) return [{ text: body, start: 0, end: body.length }];
  const pieces: { text: string; start: number; end: number }[] = [];
  const paragraphs = body.split(/\n{2,}/);
  let offset = 0;
  let buf = "";
  let bufStart = 0;
  for (const p of paragraphs) {
    if (buf && buf.length + p.length > CHUNK_CHARS) {
      pieces.push({ text: buf, start: bufStart, end: bufStart + buf.length });
      buf = "";
    }
    if (!buf) bufStart = offset;
    buf += (buf ? "\n\n" : "") + p;
    offset += p.length + 2;
  }
  if (buf) pieces.push({ text: buf, start: bufStart, end: bufStart + buf.length });
  return pieces;
}

function coverageStrengthOf(status: string): number {
  const map: Record<string, number> = { NONE: 0, MENTION_ONLY: 1, WEAK: 2, UNSUPPORTED: 2, OUTDATED: 2, PARTIAL: 3, OVERSATURATED: 3, STRONG: 5 };
  return map[status] ?? 0;
}

function titleSimilar(a: string, b: string): boolean {
  const norm = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, "").trim();
  const na = norm(a);
  const nb = norm(b);
  if (na === nb) return true;
  const ta = new Set(na.split(/\s+/).filter((t) => t.length >= 4));
  const tb = new Set(nb.split(/\s+/).filter((t) => t.length >= 4));
  if (ta.size === 0 || tb.size === 0) return false;
  let inter = 0;
  for (const t of ta) if (tb.has(t)) inter++;
  return inter / Math.min(ta.size, tb.size) >= 0.8;
}

// Re-export for scripts that want the version.
export { detectInjection };
