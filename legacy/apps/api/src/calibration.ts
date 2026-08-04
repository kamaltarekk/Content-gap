// Deterministic calibration metrics for the evaluation framework. All thresholds are labeled
// HYPOTHESES, not industry benchmarks.

interface GapRow {
  id: string;
  gapType: string;
  evidenceStatus: string;
  cohortId: string | null;
  journeyStage: string;
}
interface EvalRow {
  gapId: string | null;
  validityRating: number;
  commercialRelevanceRating: number;
  noveltyRating: number;
  evidenceQualityRating: number;
  actionabilityRating: number;
  acceptedIntoPlan: boolean;
  evaluatorName: string;
}

const RATING_HYPOTHESES = {
  topTenValidity4or5: 0.7,
  topTenRelevance4or5: 0.7,
  acceptanceRate: 0.6,
  invalidEvidenceRate: 0.1,
  interRaterAgreement: 0.6,
  shadowFalseNegativeRate: 0.2,
};

export function computeCalibration(gapsRows: GapRow[], evals: EvalRow[]) {
  const n = evals.length;
  const avg = (sel: (e: EvalRow) => number) => (n ? round(evals.reduce((s, e) => s + sel(e), 0) / n) : 0);
  const ratingAverages = {
    validity: avg((e) => e.validityRating),
    commercialRelevance: avg((e) => e.commercialRelevanceRating),
    novelty: avg((e) => e.noveltyRating),
    evidenceQuality: avg((e) => e.evidenceQualityRating),
    actionability: avg((e) => e.actionabilityRating),
  };

  const rate = (pred: (e: EvalRow) => boolean) => (n ? round(evals.filter(pred).length / n) : 0);
  const validity4or5 = rate((e) => e.validityRating >= 4);
  const relevance4or5 = rate((e) => e.commercialRelevanceRating >= 4);
  const acceptanceRate = rate((e) => e.acceptedIntoPlan);
  const invalidEvidenceRate = rate((e) => e.evidenceQualityRating <= 2);

  const byGapType = groupAvg(gapsRows, evals, (g) => g.gapType);
  const byEvidenceStatus = groupAvg(gapsRows, evals, (g) => g.evidenceStatus);
  const byCohortStage = groupAvg(gapsRows, evals, (g) => `${g.cohortId}|${g.journeyStage}`);

  const kappa = quadraticWeightedKappa(evals);

  return {
    counts: { evaluations: n, gaps: gapsRows.length },
    ratingAverages,
    validity4or5,
    relevance4or5,
    acceptanceRate,
    invalidEvidenceRate,
    interRaterKappa: kappa,
    byGapType,
    byEvidenceStatus,
    byCohortStage,
    thresholdsAreHypotheses: true,
    thresholds: RATING_HYPOTHESES,
    thresholdChecks: {
      validity: validity4or5 >= RATING_HYPOTHESES.topTenValidity4or5,
      relevance: relevance4or5 >= RATING_HYPOTHESES.topTenRelevance4or5,
      acceptance: acceptanceRate >= RATING_HYPOTHESES.acceptanceRate,
      evidence: invalidEvidenceRate < RATING_HYPOTHESES.invalidEvidenceRate,
      agreement: kappa === null ? null : kappa >= RATING_HYPOTHESES.interRaterAgreement,
    },
  };
}

function groupAvg(gapsRows: GapRow[], evals: EvalRow[], keyFn: (g: GapRow) => string) {
  const gapById = new Map(gapsRows.map((g) => [g.id, g]));
  const buckets = new Map<string, number[]>();
  for (const e of evals) {
    if (!e.gapId) continue;
    const g = gapById.get(e.gapId);
    if (!g) continue;
    const key = keyFn(g);
    const arr = buckets.get(key) ?? [];
    arr.push(e.validityRating);
    buckets.set(key, arr);
  }
  return [...buckets.entries()].map(([key, arr]) => ({ key, avgValidity: round(arr.reduce((s, x) => s + x, 0) / arr.length), count: arr.length }));
}

/** Quadratic weighted Cohen's kappa on validity between the first two evaluators per gap. */
function quadraticWeightedKappa(evals: EvalRow[]): number | null {
  const byGap = new Map<string, number[]>();
  for (const e of evals) {
    if (!e.gapId) continue;
    const arr = byGap.get(e.gapId) ?? [];
    arr.push(e.validityRating);
    byGap.set(e.gapId, arr);
  }
  const pairs = [...byGap.values()].filter((a) => a.length >= 2).map((a) => [a[0]!, a[1]!] as [number, number]);
  if (pairs.length < 2) return null;
  const K = 5;
  const O = Array.from({ length: K }, () => new Array(K).fill(0));
  const r1 = new Array(K).fill(0);
  const r2 = new Array(K).fill(0);
  for (const [a, b] of pairs) {
    O[a - 1]![b - 1] += 1;
    r1[a - 1] += 1;
    r2[b - 1] += 1;
  }
  const total = pairs.length;
  let num = 0;
  let den = 0;
  for (let i = 0; i < K; i++) {
    for (let j = 0; j < K; j++) {
      const w = ((i - j) * (i - j)) / ((K - 1) * (K - 1));
      const e = (r1[i] * r2[j]) / total;
      num += w * O[i]![j];
      den += w * e;
    }
  }
  if (den === 0) return 1;
  return round(1 - num / den);
}

function round(n: number): number {
  return Math.round(n * 1000) / 1000;
}
