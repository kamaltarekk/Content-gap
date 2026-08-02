import { type AppConfig, loadConfig } from "@cgi/shared";
import { AnthropicLlmProvider } from "./anthropic-provider.js";
import { LocalEmbeddingProvider } from "./embeddings.js";
import { FakeLlmProvider } from "./fake-provider.js";
import type { EmbeddingProvider, LlmProvider } from "./types.js";

export * from "./types.js";
export * from "./heuristics.js";
export { FakeLlmProvider } from "./fake-provider.js";
export { AnthropicLlmProvider } from "./anthropic-provider.js";
export { LocalEmbeddingProvider, cosineSimilarity } from "./embeddings.js";
export { validateResponse, estimateTokens } from "./validate.js";

export function createLlmProvider(config: AppConfig = loadConfig()): LlmProvider {
  if (config.llmProvider === "anthropic") {
    if (!config.anthropicApiKey) {
      throw new Error("LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY");
    }
    return new AnthropicLlmProvider(config.anthropicApiKey, config.anthropicModel);
  }
  return new FakeLlmProvider();
}

export function createEmbeddingProvider(config: AppConfig = loadConfig()): EmbeddingProvider {
  return new LocalEmbeddingProvider(config.embeddingDim);
}
