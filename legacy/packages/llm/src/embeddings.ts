import { createHash } from "node:crypto";
import type { EmbeddingProvider } from "./types.js";

/**
 * Deterministic, offline, multilingual embedding. Character 3-gram (+ token) hashing into
 * `dim` buckets with signed weights, then L2-normalized. Works for Arabic, English, and mixed
 * text because it operates on Unicode code points, not a language-specific tokenizer. This is a
 * "no paid API" v0 stand-in; the interface allows swapping a real local model later.
 */
export class LocalEmbeddingProvider implements EmbeddingProvider {
  readonly name = "local-hash";
  constructor(readonly dim = 384) {}

  async embed(texts: string[]): Promise<number[][]> {
    return texts.map((t) => this.embedOne(t));
  }

  private embedOne(text: string): number[] {
    const vec = new Float64Array(this.dim);
    const norm = normalize(text);
    // word tokens
    for (const tok of norm.split(/\s+/).filter(Boolean)) {
      accumulate(vec, `w:${tok}`, this.dim);
    }
    // char 3-grams (captures Arabic morphology + partial matches)
    const chars = [...norm.replace(/\s+/g, " ")];
    for (let i = 0; i + 3 <= chars.length; i++) {
      accumulate(vec, `g:${chars[i]}${chars[i + 1]}${chars[i + 2]}`, this.dim);
    }
    // L2 normalize
    let sum = 0;
    for (let i = 0; i < this.dim; i++) sum += vec[i]! * vec[i]!;
    const len = Math.sqrt(sum) || 1;
    const out = new Array<number>(this.dim);
    for (let i = 0; i < this.dim; i++) out[i] = vec[i]! / len;
    return out;
  }
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFKC")
    // strip Arabic diacritics (tashkeel) for robustness
    .replace(/[ً-ٰٟ]/g, "");
}

function accumulate(vec: Float64Array, feature: string, dim: number): void {
  const h = createHash("md5").update(feature).digest();
  const bucket = ((h[0]! << 8) | h[1]!) % dim;
  const sign = h[2]! & 1 ? 1 : -1;
  vec[bucket] = (vec[bucket] ?? 0) + sign;
}

export function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) dot += a[i]! * b[i]!;
  return dot; // vectors are already L2-normalized
}
