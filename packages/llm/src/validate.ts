import { type AllowedIds, validateIdReferences } from "@cgi/shared";
import type { z } from "zod";

/**
 * Every model response passes through here: strict Zod parse, then the hard ID-reference
 * guard (no unknown chunk/cohort/content-unit ids). Applies to fake AND real providers.
 */
export function validateResponse<S extends z.ZodTypeAny>(schema: S, raw: unknown, allowed: AllowedIds): z.infer<S> {
  const parsed = schema.parse(raw) as z.infer<S>; // throws ZodError on schema mismatch
  validateIdReferences(parsed, allowed); // throws UnknownIdError on stray ids
  return parsed;
}

export function estimateTokens(text: string): number {
  // ~4 chars/token is a reasonable cross-language approximation for cost accounting.
  return Math.max(1, Math.ceil(text.length / 4));
}
