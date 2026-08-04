import { useState } from "react";
import { apiPost } from "../api/client";

interface Finding {
  id: string;
  dimension: string;
  subject: string;
  presence: string;
  finding_status: string;
  confidence: string;
  is_public_proxy: boolean;
  summary: string;
  evidence_span_ids: string[];
}
interface Diagnosis {
  id: string;
  limitation_banner: string;
  sample_sufficiency: string;
  sample_piece_count: number;
  audits: {
    sample: { sufficiency: string; piece_count: number; channels: string[]; collection_status: string | null; blocked: number; failed: number };
    presence: { topic: string; presence: string }[];
    content_cards: { content_piece_id: string; content_format: string; snippet: string }[];
  };
  findings: Finding[];
}

// Competitor diagnosis viewer. Every view leads with the mandatory public-evidence limitation
// banner (spec §15.1). Absence is shown as "not_found_in_sample", never as a definitive claim, and
// no finding is presented as an observed fact.
export default function CompetitorDiagnosis() {
  const [projectId, setProjectId] = useState("");
  const [entityId, setEntityId] = useState("");
  const [diag, setDiag] = useState<Diagnosis | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setErr(null);
    try {
      setDiag(await apiPost<Diagnosis>(`/api/v1/projects/${projectId}/competitors/${entityId}/diagnosis`, {}));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Competitor diagnosis — تشخيص المنافس</h2>
      <input
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.25rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <input
        placeholder="competitor entity id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.25rem 0" }}
        value={entityId}
        onChange={(e) => setEntityId(e.target.value)}
      />
      <button onClick={run}>Run competitor diagnosis</button>
      {err && <p style={{ color: "crimson" }}>{err}</p>}

      {diag && (
        <>
          <p style={{ background: "#fff3cd", padding: "0.75rem", borderRadius: 6 }}>⚠️ {diag.limitation_banner}</p>
          <p>
            Sample sufficiency: <strong>{diag.sample_sufficiency}</strong> · pieces:{" "}
            {diag.sample_piece_count} · channels: {diag.audits.sample.channels.join(", ") || "—"} · collection:{" "}
            {diag.audits.sample.collection_status ?? "—"} (blocked {diag.audits.sample.blocked}, failed{" "}
            {diag.audits.sample.failed})
          </p>

          <h3>Presence in the analyzed public sample</h3>
          <ul>
            {diag.audits.presence.map((p) => (
              <li key={p.topic}>
                {p.topic}: <strong>{p.presence}</strong>
              </li>
            ))}
          </ul>

          <h3>Findings (observable only — never an observed fact)</h3>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={cell}>Dimension</th>
                <th style={cell}>Presence</th>
                <th style={cell}>Status</th>
                <th style={cell}>Public proxy</th>
                <th style={cell}>Summary</th>
              </tr>
            </thead>
            <tbody>
              {diag.findings.map((f) => (
                <tr key={f.id}>
                  <td style={cell}>{f.dimension}</td>
                  <td style={cell}>{f.presence}</td>
                  <td style={cell}>{f.finding_status}</td>
                  <td style={cell}>{f.is_public_proxy ? "yes" : "—"}</td>
                  <td style={cell} dir="auto">
                    {f.summary}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

const cell: React.CSSProperties = { border: "1px solid #ccc", padding: "0.4rem", textAlign: "left", verticalAlign: "top" };
