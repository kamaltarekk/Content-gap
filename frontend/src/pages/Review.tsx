import { useState } from "react";
import { apiGet, apiPost } from "../api/client";

interface Classification {
  id: string;
  content_piece_id: string;
  dimension: string;
  proposed_value: string | null;
  approved_value: string | null;
  confidence: string;
  review_status: string;
}

// Classification review queue: approve/reject AI proposals. The human decision is stored
// separately (approved_value) and never overwrites the AI proposal.
export default function Review() {
  const [projectId, setProjectId] = useState("");
  const [rows, setRows] = useState<Classification[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setErr(null);
    try {
      setRows(await apiGet<Classification[]>(`/api/v1/projects/${projectId}/classification/review-queue`));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }
  async function decide(id: string, decision: "approved" | "rejected") {
    await apiPost(`/api/v1/classifications/${id}/review`, { decision });
    await load();
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 860, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Classification review — مراجعة التصنيف</h2>
      <input
        dir="auto"
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.5rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <button onClick={load}>Load review queue</button>
      {err && <p style={{ color: "crimson" }}>{err}</p>}
      <table style={{ width: "100%", marginTop: "1rem", borderCollapse: "collapse" }}>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id} style={{ borderTop: "1px solid #ddd" }}>
              <td dir="auto">{c.dimension}</td>
              <td dir="auto"><strong>{c.proposed_value}</strong> · {c.confidence}</td>
              <td>
                <button onClick={() => decide(c.id, "approved")}>Approve</button>{" "}
                <button onClick={() => decide(c.id, "rejected")}>Reject</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p style={{ color: "#666" }}>No pending classifications (high-confidence proposals auto-accept).</p>}
    </section>
  );
}
