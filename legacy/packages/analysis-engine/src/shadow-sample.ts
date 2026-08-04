import { createHash } from "node:crypto";

// Deterministic shadow-sample selection: at least min(5, ceil(20% of pool)) rejected/low-ranked
// candidates, chosen by a stable hash of (runId, candidateId) so runs are reproducible and the
// original rank is not revealed by the selection order.

export function selectShadowSample<T extends { id: string }>(pool: T[], runId: string): T[] {
  if (pool.length === 0) return [];
  const target = Math.min(pool.length, Math.max(1, Math.min(5, Math.ceil(pool.length * 0.2))));
  const ranked = [...pool]
    .map((c) => ({ c, key: createHash("sha256").update(`${runId}:${c.id}`).digest("hex") }))
    .sort((a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
  return ranked.slice(0, target).map((r) => r.c);
}
