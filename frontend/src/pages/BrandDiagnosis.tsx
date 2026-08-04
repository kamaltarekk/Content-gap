import { useState } from "react";
import { apiGet, apiPost } from "../api/client";

interface ReadinessDim {
  dimension: string;
  score: number;
  confidence: string;
  rationale: string;
  evidence_span_id: string | null;
}
interface Finding {
  id: string;
  dimension: string;
  subject: string;
  severity: string | null;
  confidence: string;
  finding_status: string;
  summary: string;
  limitations: string | null;
  is_non_content_blocker: boolean;
  evidence_span_ids: string[];
}
interface Diagnosis {
  id: string;
  primary_bottleneck: string;
  readiness: { grade: string | null; dimensions: ReadinessDim[] };
  audits: {
    sales_elements: { bottleneck: string; elements: { element: string; coverage_score: number; relevant_to_bottleneck: boolean }[] };
    decision_alignment: { aligned: number; not_aligned: number };
  };
  findings: Finding[];
  limitations: string;
}

// Brand diagnosis viewer: dimension scores are shown BEFORE the A–D grade (spec §16.5); every
// finding shows severity and confidence in separate columns (never collapsed) and links to its
// evidence spans. The page renders limitations and never shows any strategy/recommendation.
export default function BrandDiagnosis() {
  const [projectId, setProjectId] = useState("");
  const [diag, setDiag] = useState<Diagnosis | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setErr(null);
    try {
      setDiag(await apiPost<Diagnosis>(`/api/v1/projects/${projectId}/brand-diagnosis`, {}));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }
  async function loadLatest() {
    setErr(null);
    try {
      const list = await apiGet<{ id: string }[]>(`/api/v1/projects/${projectId}/brand-diagnosis`);
      if (list[0]) setDiag(await apiGet<Diagnosis>(`/api/v1/brand-diagnosis/${list[0].id}`));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Brand diagnosis — تشخيص العلامة</h2>
      <input
        dir="auto"
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.5rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button onClick={run}>Run diagnosis</button>
        <button onClick={loadLatest}>Load latest</button>
      </div>
      {err && <p style={{ color: "crimson" }}>{err}</p>}

      {diag && (
        <>
          <h3>
            Readiness scorecard {diag.readiness.grade ? `— grade ${diag.readiness.grade.toUpperCase()}` : "— (insufficient evidence)"}
          </h3>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={cell}>Dimension</th>
                <th style={cell}>Score</th>
                <th style={cell}>Confidence</th>
                <th style={cell}>Rationale</th>
              </tr>
            </thead>
            <tbody>
              {diag.readiness.dimensions.map((d) => (
                <tr key={d.dimension}>
                  <td style={cell}>{d.dimension}</td>
                  <td style={cell}>{d.score}/10</td>
                  <td style={cell}>{d.confidence}</td>
                  <td style={cell} dir="auto">
                    {d.rationale}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Sales-element coverage (bottleneck: {diag.audits.sales_elements.bottleneck})</h3>
          <ul>
            {diag.audits.sales_elements.elements
              .filter((e) => e.relevant_to_bottleneck)
              .map((e) => (
                <li key={e.element}>
                  {e.element}: {e.coverage_score}/10
                </li>
              ))}
          </ul>

          <h3>Findings (severity and confidence separate)</h3>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={cell}>Dimension</th>
                <th style={cell}>Severity</th>
                <th style={cell}>Confidence</th>
                <th style={cell}>Finding</th>
                <th style={cell}>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {diag.findings.map((f) => (
                <tr key={f.id} style={f.is_non_content_blocker ? { background: "#fff3cd" } : undefined}>
                  <td style={cell}>{f.dimension}</td>
                  <td style={cell}>{f.severity ?? "—"}</td>
                  <td style={cell}>{f.confidence}</td>
                  <td style={cell} dir="auto">
                    {f.summary}
                  </td>
                  <td style={cell}>{f.evidence_span_ids.length} span(s)</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p dir="auto" style={{ marginTop: "1rem", fontStyle: "italic", color: "#555" }}>
            {diag.limitations}
          </p>
        </>
      )}
    </section>
  );
}

const cell: React.CSSProperties = { border: "1px solid #ccc", padding: "0.4rem", textAlign: "left", verticalAlign: "top" };
