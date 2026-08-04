import { computePriorityScore, priorityLabelFor, type RankingComponents } from "@cgi/shared";

// Thin deterministic wrapper around the shared heuristic so the engine has one call site.
export function prioritize(components: RankingComponents, rejected = false) {
  const score = computePriorityScore(components);
  return { score, label: priorityLabelFor(score, rejected) };
}
