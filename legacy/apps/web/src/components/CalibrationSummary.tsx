import type { Calibration, ThresholdChecks } from "../types";
import { pct } from "../utils";

function CheckPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={ok ? "status-ok" : "status-bad"}>
      {ok ? "✓" : "✗"} {label}
    </span>
  );
}

const CHECK_LABELS: { key: keyof ThresholdChecks; label: string }[] = [
  { key: "validity", label: "Validity" },
  { key: "relevance", label: "Relevance" },
  { key: "acceptance", label: "Acceptance" },
  { key: "evidence", label: "Evidence" },
  { key: "agreement", label: "Agreement" },
];

export function CalibrationSummary({
  calibration,
}: {
  calibration: Calibration;
}) {
  const c = calibration;
  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Calibration summary</h2>
      <div className="callout callout-warn">
        Thresholds below are <strong>HYPOTHESES, not benchmarks</strong>. They
        are proposed pass/fail lines for a v0 product, not validated industry
        standards.
      </div>

      <div className="grid-2">
        <div>
          <h3>Rating averages</h3>
          <table>
            <tbody>
              <tr>
                <td>Validity</td>
                <td>{c.ratingAverages.validity.toFixed(2)}</td>
              </tr>
              <tr>
                <td>Commercial relevance</td>
                <td>{c.ratingAverages.commercialRelevance.toFixed(2)}</td>
              </tr>
              <tr>
                <td>Novelty</td>
                <td>{c.ratingAverages.novelty.toFixed(2)}</td>
              </tr>
              <tr>
                <td>Evidence quality</td>
                <td>{c.ratingAverages.evidenceQuality.toFixed(2)}</td>
              </tr>
              <tr>
                <td>Actionability</td>
                <td>{c.ratingAverages.actionability.toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <h3>Headline metrics</h3>
          <table>
            <tbody>
              <tr>
                <td>Validity 4 or 5</td>
                <td>{pct(c.validity4or5)}</td>
              </tr>
              <tr>
                <td>Relevance 4 or 5</td>
                <td>{pct(c.relevance4or5)}</td>
              </tr>
              <tr>
                <td>Acceptance rate</td>
                <td>{pct(c.acceptanceRate)}</td>
              </tr>
              <tr>
                <td>Invalid evidence rate</td>
                <td>{pct(c.invalidEvidenceRate)}</td>
              </tr>
              <tr>
                <td>Inter-rater kappa</td>
                <td>
                  {c.interRaterKappa === null
                    ? "n/a (need 2+ raters)"
                    : c.interRaterKappa.toFixed(2)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <h3 style={{ marginTop: 16 }}>Threshold checks (hypotheses)</h3>
      <div className="meta-row">
        {CHECK_LABELS.map((ch) => (
          <CheckPill
            key={ch.key}
            ok={c.thresholdChecks[ch.key]}
            label={ch.label}
          />
        ))}
      </div>
    </div>
  );
}
