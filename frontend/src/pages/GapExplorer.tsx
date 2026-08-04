import { useState } from "react";
import { apiPost } from "../api/client";

interface Gap {
  id: string;
  territory: string;
  gap_type: string;
  gap_status: string;
  severity: string;
  severity_score: number;
  confidence: string;
  confidence_score: number;
  root_cause_type: string;
  summary: string;
  brand_score: number | null;
  best_competitor_score: number | null;
  evidence_span_ids: string[];
  alternative_explanations: { text: string; status: string }[];
  competitor_only_signal: boolean;
  requires_human_approval: boolean;
}
interface Run {
  id: string;
  rule_version: string;
  primary_bottleneck: string;
  gaps: Gap[];
}

// Gap explorer. Severity and confidence are shown as separate columns (never one number). A gap is
// never "confirmed" by the engine — a critical gap requires explicit human approval, offered here.
export default function GapExplorer() {
  const [projectId, setProjectId] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function runAnalysis() {
    setErr(null);
    try {
      setRun(await apiPost<Run>(`/api/v1/projects/${projectId}/gap-analysis`, {}));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }
  async function approve(gapId: string) {
    await apiPost(`/api/v1/gaps/${gapId}/approve`, {});
    await runAnalysis();
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 1000, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Gap explorer — مستكشف الفجوات</h2>
      <input
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.5rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <button onClick={runAnalysis}>Run gap analysis</button>
      {err && <p style={{ color: "crimson" }}>{err}</p>}

      {run && (
        <>
          <p>
            rule_version: <code>{run.rule_version}</code> · bottleneck: {run.primary_bottleneck} · gaps:{" "}
            {run.gaps.length}
          </p>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 14 }}>
            <thead>
              <tr>
                <th style={cell}>Territory</th>
                <th style={cell}>Type</th>
                <th style={cell}>Status</th>
                <th style={cell}>Severity</th>
                <th style={cell}>Confidence</th>
                <th style={cell}>Root cause</th>
                <th style={cell}>Evidence</th>
                <th style={cell}>Alt. expl.</th>
                <th style={cell}></th>
              </tr>
            </thead>
            <tbody>
              {run.gaps.map((g) => (
                <tr key={g.id}>
                  <td style={cell}>{g.territory}</td>
                  <td style={cell}>{g.gap_type}</td>
                  <td style={cell}>{g.gap_status}</td>
                  <td style={cell}>
                    {g.severity} ({g.severity_score})
                  </td>
                  <td style={cell}>
                    {g.confidence} ({g.confidence_score}){g.competitor_only_signal ? " · comp-only" : ""}
                  </td>
                  <td style={cell}>{g.root_cause_type}</td>
                  <td style={cell}>{g.evidence_span_ids.length}</td>
                  <td style={cell}>{g.alternative_explanations.length}</td>
                  <td style={cell}>
                    {g.requires_human_approval ? <button onClick={() => approve(g.id)}>Approve</button> : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontStyle: "italic", color: "#555" }}>
            The engine never confirms a gap automatically. Severity and confidence are independent; a
            competitor-only signal is capped at low confidence.
          </p>
        </>
      )}
    </section>
  );
}

const cell: React.CSSProperties = { border: "1px solid #ccc", padding: "0.35rem", textAlign: "left", verticalAlign: "top" };
