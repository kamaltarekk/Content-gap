import { createHash } from "node:crypto";

/**
 * Deterministic content hash used to gate snapshot creation and dedup.
 * Normalizes whitespace first so trivially-different-but-equal content hashes equal.
 */
export function contentHash(content: string): string {
  const normalized = content.replace(/\r\n/g, "\n").replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim();
  return createHash("sha256").update(normalized, "utf8").digest("hex");
}

/** SHA-256 of a raw string, no normalization (used for token hashing). */
export function sha256(raw: string): string {
  return createHash("sha256").update(raw, "utf8").digest("hex");
}

/** Constant-time string comparison for secrets. */
export function timingSafeEqualHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}
