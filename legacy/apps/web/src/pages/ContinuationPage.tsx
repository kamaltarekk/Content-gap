import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { getActiveProjectId } from "../project";
import type { Calibration, Run, ThresholdChecks } from "../types";
import { CalibrationSummary } from "../components/CalibrationSummary";
import { ErrorNote, Spinner } from "../components/ui";
import { pct } from "../utils";

type Recommendation = "CONTINUE" | "REVISE" | "KILL_OR_REFRAME";

function countPassed(checks: ThresholdChecks): number {
  return Object.values(checks).filter(Boolean).length;
}

function decide(cal: Calibration): {
  rec: Recommendation;
  rationale: string;
} {
  const passed = countPassed(cal.thresholdChecks);
  const total = Object.keys(cal.thresholdChecks).length;
  const acceptance = cal.acceptanceRate <= 1
    ? cal.acceptanceRate
    : cal.acceptanceRate / 100;

  if (passed >= total - 1 && acceptance >= 0.5) {
    return {
      rec: "CONTINUE",
      rationale: `${passed}/${total} threshold hypotheses pass and acceptance rate is ${pct(cal.acceptanceRate)}. The system appears to be producing gaps evaluators would act on.`,
    };
  }
  if (passed >= Math.ceil(total / 2)) {
    return {
      rec: "REVISE",
      rationale: `${passed}/${total} threshold hypotheses pass. Mixed signal — some dimensions clear the proposed bar while others do not. Revise ranking / evidence rules before scaling.`,
    };
  }
  return {
    rec: "KILL_OR_REFRAME",
    rationale: `Only ${passed}/${total} threshold hypotheses pass and acceptance rate is ${pct(cal.acceptanceRate)}. The current framing may not be producing usable gaps; consider reframing the problem or offer.`,
  };
}

const REC_META: Record<
  Recommendation,
  { label: string; callout: string }
> = {
  CONTINUE: { label: "Continue", callout: "callout-info" },
  REVISE: { label: "Revise", callout: "callout-warn" },
  KILL_OR_REFRAME: {
    label: "Kill or Reframe",
    callout: "callout-danger",
  },
};

export function ContinuationPage() {
  const projectId = getActiveProjectId() ?? "";
  const evalQuery = useQuery({
    queryKey: ["evaluations", projectId],
    queryFn: () => api.getEvaluations(projectId),
  });
  const runsQuery = useQuery({
    queryKey: ["runs", projectId],
    queryFn: () => api.getRuns(projectId),
  });

  if (evalQuery.isLoading || runsQuery.isLoading) return <Spinner />;
  if (evalQuery.isError) return <ErrorNote error={evalQuery.error} />;
  if (runsQuery.isError) return <ErrorNote error={runsQuery.error} />;

  const cal = evalQuery.data?.calibration;
  const runs: Run[] = runsQuery.data ?? [];
  if (!cal) return <ErrorNote error={new Error("No calibration data")} />;

  const { rec, rationale } = decide(cal);
  const meta = REC_META[rec];

  const completedRuns = runs.filter((r) => r.status === "COMPLETED").length;
  const totalPublished = runs.reduce(
    (sum, r) =>
      sum +
      (typeof r.outputCountsJson?.publishedGaps === "number"
        ? r.outputCountsJson.publishedGaps
        : 0),
    0,
  );

  return (
    <div>
      <h1>Continuation report</h1>
      <p className="subtitle">
        A Continue / Revise / Kill-or-Reframe recommendation derived from
        calibration threshold checks and acceptance rate.
      </p>

      <div className="callout callout-warn">
        This report is a set of <strong>PROPOSED HYPOTHESES</strong>, not ground
        truth. The thresholds it relies on are unvalidated v0 assumptions. Treat
        the recommendation as a prompt for human judgment.
      </div>

      <div className={`callout ${meta.callout}`}>
        <h2 style={{ margin: "0 0 6px" }}>
          Proposed decision: {meta.label}
        </h2>
        <p style={{ margin: 0 }}>{rationale}</p>
      </div>

      <div className="card">
        <h3>Signals used</h3>
        <div className="table-wrap">
          <table>
            <tbody>
              <tr>
                <td>Threshold checks passed</td>
                <td>
                  {countPassed(cal.thresholdChecks)} /{" "}
                  {Object.keys(cal.thresholdChecks).length}
                </td>
              </tr>
              <tr>
                <td>Acceptance rate</td>
                <td>{pct(cal.acceptanceRate)}</td>
              </tr>
              <tr>
                <td>Validity 4 or 5</td>
                <td>{pct(cal.validity4or5)}</td>
              </tr>
              <tr>
                <td>Invalid evidence rate</td>
                <td>{pct(cal.invalidEvidenceRate)}</td>
              </tr>
              <tr>
                <td>Completed runs</td>
                <td>{completedRuns}</td>
              </tr>
              <tr>
                <td>Total published gaps (all runs)</td>
                <td>{totalPublished}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Framework (hypotheses)</h3>
        <ul className="list-plain">
          <li>
            <strong>Continue</strong> — nearly all threshold hypotheses pass and
            evaluators accept a majority of gaps. Keep the current pipeline and
            scale ingestion.
          </li>
          <li>
            <strong>Revise</strong> — mixed signal. Adjust ranking weights,
            evidence rules, or cohort definitions and re-measure before scaling.
          </li>
          <li>
            <strong>Kill or Reframe</strong> — most hypotheses fail. Re-examine
            the problem framing, offer, or source mix before further
            investment.
          </li>
        </ul>
      </div>

      <CalibrationSummary calibration={cal} />
    </div>
  );
}
