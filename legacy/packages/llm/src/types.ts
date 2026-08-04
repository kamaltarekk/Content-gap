import type {
  CandidateGapResponse,
  CoverageResponse,
  CritiqueVerdict,
  DecisionSupportResponse,
  ExtractionResponse,
  JourneyStage,
} from "@cgi/shared";

export interface LlmUsage {
  inputTokens: number;
  outputTokens: number;
}
export interface LlmResult<T> {
  data: T;
  usage: LlmUsage;
  /** Source spans that looked like injected instructions (logged, never obeyed). */
  suspiciousInstructions: string[];
}

// ---- Operation inputs (assembled deterministically by the analysis engine) ----

export interface ExtractionInput {
  contentUnit: { id: string; title: string; body: string; language: string; ownerType: string };
  chunks: { id: string; text: string }[];
  cohorts: { id: string; name: string; keywords: string[] }[];
}

export interface VocSignalInput {
  chunkId: string;
  text: string;
  cohortId: string | null;
}
export interface DecisionSupportInput {
  cohorts: {
    id: string;
    name: string;
    keywords: string[];
    objections: string[];
    decisionCriteria: string[];
    activeProblem: string;
    currentBelief: string;
    desiredOutcome: string;
  }[];
  brief: { approvedProof: string[]; commercialPriority: string };
  vocSignals: VocSignalInput[];
}

export interface CoverageInput {
  needs: { needKey: string; cohortId: string; journeyStage: JourneyStage; normalizedNeed: string; description: string }[];
  // Shortlisted owned content units (already narrowed by semantic retrieval).
  ownedUnits: {
    id: string;
    title: string;
    text: string;
    hasProofSignal: boolean;
    connectsToOffer: boolean;
    hasCta: boolean;
    isOutdated: boolean;
    hasUnsupportedClaim: boolean;
    matchedNeedKeys: string[];
  }[];
}

export interface CandidateInput {
  cohorts: { id: string; name: string; priority: number }[];
  needs: {
    needKey: string;
    cohortId: string;
    journeyStage: JourneyStage;
    normalizedNeed: string;
    needType: string;
    coverageStatus: string;
    demandChunkIds: string[];
    coverageUnitIds: string[];
  }[];
  // Chunk text available for evidence quoting (the ONLY chunks the model may cite).
  chunks: { id: string; text: string; ownerType: string }[];
}

export interface CritiqueInput {
  candidate: {
    title: string;
    gapType: string;
    cohortId: string;
    coverageStatus: string;
    hasVerifiedCustomerDemand: boolean;
    hasVerifiedOwnedCoverageAlready: boolean;
    isDuplicateOfTitle: string | null;
    looksLikeNonContentProblem: boolean;
  };
}

// ---- Provider interfaces ----

export interface LlmProvider {
  readonly name: string;
  readonly model: string;
  extract(input: ExtractionInput): Promise<LlmResult<ExtractionResponse>>;
  mapDecisionSupport(input: DecisionSupportInput): Promise<LlmResult<DecisionSupportResponse>>;
  classifyCoverage(input: CoverageInput): Promise<LlmResult<CoverageResponse>>;
  generateCandidates(input: CandidateInput): Promise<LlmResult<CandidateGapResponse>>;
  critique(input: CritiqueInput): Promise<LlmResult<CritiqueVerdict>>;
}

export interface EmbeddingProvider {
  readonly name: string;
  readonly dim: number;
  embed(texts: string[]): Promise<number[][]>;
}
