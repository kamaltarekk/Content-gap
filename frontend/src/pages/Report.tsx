import { useState } from "react";
import { apiPost } from "../api/client";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:3001";

interface Report {
  id: string;
  status: string;
  readiness_status: string;
  readiness_reason: string;
  version_manifest: { rule_version: string; ai_model: string; context_version_number: number | null; dataset: Record<string, number> };
  snapshot: {
    executive_diagnosis: string;
    scope_and_limitations: { brand: string; competitor_banner: string };
    critical_and_high_gaps: { territory: string; gap_type: string; severity: string; confidence: string }[];
    research_backlog: { territory: string; question: string }[];
    readiness_decision: { status: string; reason: string; unresolved_items: unknown[] };
  };
}

const READINESS_COLOR: Record<string, string> = {
  ready_for_content_strategy: "#198754",
  ready_with_unresolved_hypotheses: "#0d6efd",
  more_evidence_required: "#fd7e14",
  blocked_by_non_content_issue: "#dc3545",
};

// Final diagnostic report. Shows the strategy-readiness decision (one of four statuses), the
// evidence limitations, critical/high gaps, and the research backlog. Reports are immutable
// snapshots; exports (JSON / CSV / print-PDF) open in a new tab.
export default function Report() {
  const [projectId, setProjectId] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function generate() {
    setErr(null);
    try {
      setReport(await apiPost<Report>(`/api/v1/projects/${projectId}/reports`, {}));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Final diagnostic report — التقرير التشخيصي</h2>
      <input
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.5rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <button onClick={generate}>Generate report</button>
      {err && <p style={{ color: "crimson" }}>{err}</p>}

      {report && (
        <>
          <p
            style={{
              padding: "0.75rem",
              borderRadius: 6,
              color: "white",
              background: READINESS_COLOR[report.readiness_status] ?? "#666",
            }}
          >
            <strong>{report.readiness_status}</strong> — {report.readiness_reason}
          </p>
          <p>
            Exports:{" "}
            <a href={`${API_BASE}/api/v1/reports/${report.id}/export/json`} target="_blank" rel="noreferrer">JSON</a>
            {" · "}
            <a href={`${API_BASE}/api/v1/reports/${report.id}/export/csv`} target="_blank" rel="noreferrer">CSV</a>
            {" · "}
            <a href={`${API_BASE}/api/v1/reports/${report.id}/export/html`} target="_blank" rel="noreferrer">Print / PDF</a>
          </p>

          <h3>Executive diagnosis</h3>
          <p dir="auto">{report.snapshot.executive_diagnosis}</p>

          <h3>Scope &amp; evidence limitations</h3>
          <p dir="auto">{report.snapshot.scope_and_limitations.brand}</p>
          <p dir="auto" style={{ background: "#fff3cd", padding: "0.5rem" }}>
            {report.snapshot.scope_and_limitations.competitor_banner}
          </p>

          <h3>Critical &amp; high-priority gaps</h3>
          <ul>
            {report.snapshot.critical_and_high_gaps.map((g, i) => (
              <li key={i}>
                {g.territory} · {g.gap_type} · severity {g.severity} / confidence {g.confidence}
              </li>
            ))}
            {report.snapshot.critical_and_high_gaps.length === 0 && <li>None</li>}
          </ul>

          <h3>Research backlog (not a content calendar)</h3>
          <ul>
            {report.snapshot.research_backlog.map((b, i) => (
              <li key={i} dir="auto">
                {b.question}
              </li>
            ))}
            {report.snapshot.research_backlog.length === 0 && <li>None</li>}
          </ul>

          <h3>Version manifest</h3>
          <p>
            rule_version {report.version_manifest.rule_version} · model {report.version_manifest.ai_model} · context v
            {report.version_manifest.context_version_number ?? "—"} · pieces{" "}
            {report.version_manifest.dataset.content_pieces}
          </p>
        </>
      )}
    </section>
  );
}
