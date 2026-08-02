import Anthropic from "@anthropic-ai/sdk";
import {
  type AllowedIds,
  CandidateGapResponseSchema,
  CoverageResponseSchema,
  CritiqueVerdictSchema,
  DecisionSupportResponseSchema,
  ExtractionResponseSchema,
} from "@cgi/shared";
import { detectInjection } from "./heuristics.js";
import { SYSTEM_PREAMBLE, allowedIdsBlock, wrapSource } from "./prompts.js";
import type {
  CandidateInput,
  CoverageInput,
  CritiqueInput,
  DecisionSupportInput,
  ExtractionInput,
  LlmProvider,
  LlmResult,
} from "./types.js";
import { validateResponse } from "./validate.js";
import type { z } from "zod";

/**
 * Real provider using Anthropic's official SDK. Every call:
 *  - keeps system instructions separate from source content (delimited, declared untrusted),
 *  - forces a single JSON object,
 *  - validates the response with Zod + the unknown-ID guard.
 * The key is read from env in the backend only. Never used by the extension.
 */
export class AnthropicLlmProvider implements LlmProvider {
  readonly name = "anthropic";
  private client: Anthropic;
  constructor(
    apiKey: string,
    readonly model: string,
  ) {
    this.client = new Anthropic({ apiKey });
  }

  async extract(input: ExtractionInput): Promise<LlmResult<z.infer<typeof ExtractionResponseSchema>>> {
    const user = [
      allowedIdsBlock({ chunkIds: input.chunks.map((c) => c.id), cohortIds: input.cohorts.map((c) => c.id), contentUnitIds: [input.contentUnit.id] }),
      `contentUnitId: ${input.contentUnit.id}`,
      `cohorts: ${JSON.stringify(input.cohorts)}`,
      wrapSource("content_unit", `TITLE: ${input.contentUnit.title}\n${input.contentUnit.body}`),
      input.chunks.map((c) => `CHUNK ${c.id}:\n${wrapSource("chunk", c.text)}`).join("\n"),
      `Return JSON matching the extraction schema: {contentUnitId, language(ar|en|mixed|unknown), primaryCohortId|null, secondaryCohortIds[], journeyStages[], contentRole, signals[{type,normalizedLabel,rawText,journeyStage,cohortId|null,evidenceChunkId}], proofUsed[], claims[], cta|null}. Every evidenceChunkId MUST be one of the allowed chunk ids.`,
    ].join("\n\n");
    return this.call(ExtractionResponseSchema, user, allowedFrom(input), collectInjection(input));
  }

  async mapDecisionSupport(input: DecisionSupportInput): Promise<LlmResult<z.infer<typeof DecisionSupportResponseSchema>>> {
    const user = [
      allowedIdsBlock({ chunkIds: input.vocSignals.map((v) => v.chunkId), cohortIds: input.cohorts.map((c) => c.id) }),
      `cohorts: ${JSON.stringify(input.cohorts)}`,
      `brief: ${JSON.stringify(input.brief)}`,
      wrapSource("voc", input.vocSignals.map((v) => `[${v.chunkId}] ${v.text}`).join("\n")),
      `Derive required decision-support needs per cohort×stage primarily from brief + cohorts + VoC. Competitor context does NOT prove demand. Return JSON {needs:[{cohortId,journeyStage,needType,normalizedNeed,description,supportingChunkIds[]}]}.`,
    ].join("\n\n");
    return this.call(DecisionSupportResponseSchema, user, {
      chunkIds: new Set(input.vocSignals.map((v) => v.chunkId)),
      cohortIds: new Set(input.cohorts.map((c) => c.id)),
      contentUnitIds: new Set(),
    }, input.vocSignals.flatMap((v) => detectInjection(v.text)));
  }

  async classifyCoverage(input: CoverageInput): Promise<LlmResult<z.infer<typeof CoverageResponseSchema>>> {
    const user = [
      allowedIdsBlock({ contentUnitIds: input.ownedUnits.map((u) => u.id) }),
      `needs: ${JSON.stringify(input.needs)}`,
      input.ownedUnits.map((u) => `UNIT ${u.id} (${u.title}):\n${wrapSource("owned", u.text)}`).join("\n"),
      `Classify each need's owned coverage. Return JSON {classifications:[{needKey,coverageStatus,matchedContentUnitIds[],summary,hasProof,connectsToOffer,hasNextAction}]}. coverageStatus in NONE|MENTION_ONLY|WEAK|PARTIAL|STRONG|OUTDATED|UNSUPPORTED|OVERSATURATED.`,
    ].join("\n\n");
    return this.call(CoverageResponseSchema, user, {
      chunkIds: new Set(),
      cohortIds: new Set(),
      contentUnitIds: new Set(input.ownedUnits.map((u) => u.id)),
    }, []);
  }

  async generateCandidates(input: CandidateInput): Promise<LlmResult<z.infer<typeof CandidateGapResponseSchema>>> {
    const user = [
      allowedIdsBlock({ chunkIds: input.chunks.map((c) => c.id), cohortIds: input.cohorts.map((c) => c.id) }),
      `needs: ${JSON.stringify(input.needs)}`,
      input.chunks.map((c) => `CHUNK ${c.id} [${c.ownerType}]:\n${wrapSource("evidence", c.text)}`).join("\n"),
      `Generate candidate gaps ONLY where a need has demand evidence and coverage is not STRONG. A missing competitor topic alone is NOT a gap. Each evidence.exactQuote MUST be an exact substring of the cited chunk. Return JSON {candidates:[{cohortId,journeyStage,gapType,title,customerQuestionOrBelief,missingDecisionSupport[],commercialConsequence,recommendedContentRole,recommendedAssetType,suggestedTouchpoint,generationReason,evidence:[{role,chunkId,exactQuote}],rankingComponents:{...0..5}}]}.`,
    ].join("\n\n");
    return this.call(CandidateGapResponseSchema, user, {
      chunkIds: new Set(input.chunks.map((c) => c.id)),
      cohortIds: new Set(input.cohorts.map((c) => c.id)),
      contentUnitIds: new Set(),
    }, input.chunks.flatMap((c) => detectInjection(c.text)));
  }

  async critique(input: CritiqueInput): Promise<LlmResult<z.infer<typeof CritiqueVerdictSchema>>> {
    const user = [
      `candidate: ${JSON.stringify(input.candidate)}`,
      `Bounded critique. Decide one action: ACCEPT | DOWNGRADE | MERGE | REJECT | MARK_NON_CONTENT. Return JSON {action,reason,mergeWithTitle|null}.`,
    ].join("\n\n");
    return this.call(CritiqueVerdictSchema, user, { chunkIds: new Set(), cohortIds: new Set(), contentUnitIds: new Set() }, []);
  }

  private async call<S extends z.ZodTypeAny>(
    schema: S,
    userContent: string,
    allowed: AllowedIds,
    suspicious: string[],
  ): Promise<LlmResult<z.infer<S>>> {
    const res = await this.client.messages.create({
      model: this.model,
      max_tokens: 4096,
      system: SYSTEM_PREAMBLE,
      messages: [{ role: "user", content: userContent }],
    });
    const text = res.content.map((b) => ("text" in b ? b.text : "")).join("");
    const json = extractJson(text);
    const data = validateResponse(schema, json, allowed);
    return {
      data,
      usage: { inputTokens: res.usage.input_tokens, outputTokens: res.usage.output_tokens },
      suspiciousInstructions: suspicious,
    };
  }
}

function extractJson(text: string): unknown {
  const fenced = /```(?:json)?\s*([\s\S]*?)```/.exec(text);
  const candidate = fenced ? fenced[1]! : text;
  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start < 0 || end < 0) throw new Error("Model response contained no JSON object");
  return JSON.parse(candidate.slice(start, end + 1));
}

function allowedFrom(input: ExtractionInput): AllowedIds {
  return {
    chunkIds: new Set(input.chunks.map((c) => c.id)),
    cohortIds: new Set(input.cohorts.map((c) => c.id)),
    contentUnitIds: new Set([input.contentUnit.id]),
  };
}
function collectInjection(input: ExtractionInput): string[] {
  return [...detectInjection(input.contentUnit.body), ...input.chunks.flatMap((c) => detectInjection(c.text))];
}
