import { DEFAULT_LIMITS, type SafetyLimits } from "./limits.js";

// Central runtime config, read once from environment. No secrets are logged.

function num(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}
function bool(name: string, fallback: boolean): boolean {
  const raw = process.env[name];
  if (raw === undefined) return fallback;
  return raw === "true" || raw === "1";
}
function str(name: string, fallback: string): string {
  const raw = process.env[name];
  return raw === undefined || raw === "" ? fallback : raw;
}

export interface Pricing {
  llmInputPerMTok: number;
  llmOutputPerMTok: number;
  embeddingPerMTok: number;
}

export interface AppConfig {
  databaseUrl: string;
  api: { host: string; port: number; corsOrigins: string[] };
  llmProvider: "fake" | "anthropic";
  anthropicApiKey: string;
  anthropicModel: string;
  embeddingProvider: "local";
  embeddingDim: number;
  crawler: {
    userAgent: string;
    perDomainRps: number;
    respectRobots: boolean;
    playwrightFallback: boolean;
  };
  pricing: Pricing;
  limits: SafetyLimits;
  retentionSnapshotDays: number;
  logLevel: string;
  nodeEnv: string;
}

export function loadConfig(): AppConfig {
  const llmProvider = str("LLM_PROVIDER", "fake") === "anthropic" ? "anthropic" : "fake";
  return {
    databaseUrl: str("DATABASE_URL", "postgres://cgi:cgi@localhost:5433/cgi"),
    api: {
      host: str("API_HOST", "0.0.0.0"),
      port: num("API_PORT", 3001),
      corsOrigins: str("CORS_ORIGINS", "http://localhost:5173")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    },
    llmProvider,
    anthropicApiKey: str("ANTHROPIC_API_KEY", ""),
    anthropicModel: str("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
    embeddingProvider: "local",
    embeddingDim: num("EMBEDDING_DIM", 384),
    crawler: {
      userAgent: str("CRAWLER_USER_AGENT", "ContentGapIntelligenceBot/0.0 (+https://example.com/bot)"),
      perDomainRps: num("CRAWLER_PER_DOMAIN_RPS", 0.5),
      respectRobots: bool("CRAWLER_RESPECT_ROBOTS", true),
      playwrightFallback: bool("CRAWLER_PLAYWRIGHT_FALLBACK", false),
    },
    pricing: {
      llmInputPerMTok: num("PRICE_LLM_INPUT_PER_MTOK", 3.0),
      llmOutputPerMTok: num("PRICE_LLM_OUTPUT_PER_MTOK", 15.0),
      embeddingPerMTok: num("PRICE_EMBEDDING_PER_MTOK", 0),
    },
    limits: {
      ...DEFAULT_LIMITS,
      maxOwnedUrls: num("LIMIT_OWNED_URLS", DEFAULT_LIMITS.maxOwnedUrls),
      maxCompetitorUrls: num("LIMIT_COMPETITOR_URLS", DEFAULT_LIMITS.maxCompetitorUrls),
      maxVocRows: num("LIMIT_VOC_ROWS", DEFAULT_LIMITS.maxVocRows),
      maxChunksPerRun: num("LIMIT_MAX_CHUNKS_PER_RUN", DEFAULT_LIMITS.maxChunksPerRun),
      maxTokensPerRun: num("LIMIT_MAX_TOKENS_PER_RUN", DEFAULT_LIMITS.maxTokensPerRun),
      weeklyCostBudgetUsd: num("LIMIT_WEEKLY_COST_BUDGET_USD", DEFAULT_LIMITS.weeklyCostBudgetUsd),
    },
    retentionSnapshotDays: num("RETENTION_SNAPSHOT_DAYS", 180),
    logLevel: str("LOG_LEVEL", "info"),
    nodeEnv: str("NODE_ENV", "development"),
  };
}

export function estimateCostUsd(inputTokens: number, outputTokens: number, pricing: Pricing): number {
  const cost =
    (inputTokens / 1_000_000) * pricing.llmInputPerMTok +
    (outputTokens / 1_000_000) * pricing.llmOutputPerMTok;
  // Round to 6 decimals to keep usage records stable.
  return Math.round(cost * 1_000_000) / 1_000_000;
}
