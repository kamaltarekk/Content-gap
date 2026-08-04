import { type EmbeddingProvider, cosineSimilarity } from "@cgi/llm";

// Semantic retrieval helper used to SHORTLIST candidates before any LLM classification,
// so we never send the full corpus into a prompt. Deterministic (local embeddings).

export interface Embeddable {
  id: string;
  text: string;
}

export class Retriever {
  private vectors = new Map<string, number[]>();
  constructor(private embed: EmbeddingProvider) {}

  async index(items: Embeddable[]): Promise<void> {
    const missing = items.filter((i) => !this.vectors.has(i.id));
    if (missing.length === 0) return;
    const vecs = await this.embed.embed(missing.map((m) => m.text));
    missing.forEach((m, i) => this.vectors.set(m.id, vecs[i]!));
  }

  async topK(queryText: string, candidateIds: string[], k: number): Promise<{ id: string; score: number }[]> {
    const [qv] = await this.embed.embed([queryText]);
    const scored = candidateIds
      .map((id) => {
        const v = this.vectors.get(id);
        return v ? { id, score: cosineSimilarity(qv!, v) } : null;
      })
      .filter((x): x is { id: string; score: number } => x !== null)
      .sort((a, b) => b.score - a.score);
    return scored.slice(0, k);
  }
}

// Deterministic keyword overlap gate to avoid spurious semantic matches (short/mixed-language text).
export function keywordOverlap(a: string, b: string): boolean {
  const toks = (s: string) =>
    new Set(
      s
        .toLowerCase()
        .split(/[^\p{L}\p{N}]+/u)
        .filter((t) => t.length >= 4),
    );
  const ta = toks(a);
  const tb = toks(b);
  for (const t of ta) if (tb.has(t)) return true;
  return false;
}
