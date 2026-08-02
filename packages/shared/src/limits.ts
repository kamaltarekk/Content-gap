// Configurable safety limits for v0. Defaults here; overridable via env in config.ts.

export interface SafetyLimits {
  maxProjects: number;
  maxCohorts: number;
  maxOffers: number;
  maxCompetitors: number;
  maxOwnedUrls: number;
  maxCompetitorUrls: number;
  maxVocRows: number;
  maxPageBytes: number;
  maxFileBytes: number;
  maxChunksPerRun: number;
  maxTokensPerRun: number;
  weeklyCostBudgetUsd: number;
  maxPublishedGaps: number;
}

export const DEFAULT_LIMITS: SafetyLimits = {
  maxProjects: 1,
  maxCohorts: 2,
  maxOffers: 1,
  maxCompetitors: 3,
  maxOwnedUrls: 100,
  maxCompetitorUrls: 50,
  maxVocRows: 5000,
  maxPageBytes: 5_000_000,
  maxFileBytes: 20_000_000,
  maxChunksPerRun: 5000,
  maxTokensPerRun: 2_000_000,
  weeklyCostBudgetUsd: 25,
  maxPublishedGaps: 10,
};

export class LimitExceededError extends Error {
  constructor(
    public readonly limitName: keyof SafetyLimits,
    public readonly limitValue: number,
    public readonly attempted: number,
  ) {
    super(`Limit "${limitName}" exceeded: attempted ${attempted}, max ${limitValue}`);
    this.name = "LimitExceededError";
  }
}
