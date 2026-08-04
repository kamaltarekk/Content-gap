import type { PriorityLabel } from "./enums.js";

// Transparent, configurable ranking heuristic. This is a PRODUCT HYPOTHESIS, not a
// probability or confidence. Every component is stored and displayed to the user.

export interface RankingComponents {
  commercialImpact: number; // 0..5
  journeyBlockage: number; // 0..5
  cohortPriority: number; // 0..5
  demandStrength: number; // 0..5
  coverageDeficit: number; // 0..5
  strategicAlignment: number; // 0..5
  competitiveOpportunity: number; // 0..5
  actionability: number; // 0..5
  productionFeasibility: number; // 0..5
  learningValue: number; // 0..5
}

// Initial weights — treat as a hypothesis, tune with evaluation data.
export const RANKING_WEIGHTS: Record<keyof RankingComponents, number> = {
  commercialImpact: 3,
  journeyBlockage: 3,
  cohortPriority: 2,
  demandStrength: 2,
  coverageDeficit: 2,
  strategicAlignment: 2,
  competitiveOpportunity: 1,
  actionability: 1,
  productionFeasibility: 1,
  learningValue: 1,
};

// Max achievable score with the weights above (all components = 5). Used for labels + display.
export const MAX_PRIORITY_SCORE = Object.values(RANKING_WEIGHTS).reduce((s, w) => s + w * 5, 0); // 90

export function computePriorityScore(c: RankingComponents): number {
  let score = 0;
  for (const key of Object.keys(RANKING_WEIGHTS) as (keyof RankingComponents)[]) {
    const v = clamp05(c[key]);
    score += v * RANKING_WEIGHTS[key];
  }
  return score;
}

// Score thresholds -> label. Hypotheses, configurable. `rejected` short-circuits to P5.
export const PRIORITY_THRESHOLDS: { min: number; label: PriorityLabel }[] = [
  { min: 75, label: "P0_CRITICAL_BLOCKER" },
  { min: 62, label: "P1_PRODUCE_NOW" },
  { min: 48, label: "P2_PRODUCE_NEXT" },
  { min: 34, label: "P3_VALIDATE" },
  { min: 1, label: "P4_MONITOR" },
];

export function priorityLabelFor(score: number, rejected = false): PriorityLabel {
  if (rejected) return "P5_REJECT";
  for (const t of PRIORITY_THRESHOLDS) if (score >= t.min) return t.label;
  return "P5_REJECT";
}

function clamp05(n: number): number {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(5, Math.round(n)));
}
