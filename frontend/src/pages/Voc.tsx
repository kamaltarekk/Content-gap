import { useState } from "react";
import { apiGet, apiPost } from "../api/client";

interface VocEntry {
  id: string;
  bank_type: string;
  verbatim_phrase: string;
  occurrence_count: number;
  review_status: string;
}
interface Bank {
  bank_type: string;
  phrase_count: number;
  approved_count: number;
  confidence: string;
  confirmed_patterns: string[];
}

const BANK_TYPES = ["trigger", "objection", "motivation", "satisfaction", "complaint", "switching_reason"];

// Minimal Voice-of-Customer console: add a verbatim phrase (Arabic never rewritten), approve it,
// and read the language banks whose confidence rises only when enough real phrases are approved
// (the Phase 6 gate — repetition + review, exercised from the UI).
export default function Voc() {
  const [projectId, setProjectId] = useState("");
  const [bankType, setBankType] = useState("complaint");
  const [phrase, setPhrase] = useState("");
  const [entries, setEntries] = useState<VocEntry[]>([]);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    setErr(null);
    try {
      setEntries(await apiGet<VocEntry[]>(`/api/v1/projects/${projectId}/voc`));
      setBanks(await apiGet<Bank[]>(`/api/v1/projects/${projectId}/voc/language-banks`));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }
  async function add() {
    setErr(null);
    try {
      await apiPost(`/api/v1/projects/${projectId}/voc/manual`, { bank_type: bankType, verbatim_phrase: phrase });
      setPhrase("");
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }
  async function approve(id: string) {
    await apiPost(`/api/v1/voc/${id}/approve`, {});
    await refresh();
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 820, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Voice of Customer — صوت العميل</h2>
      <input
        dir="auto"
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.5rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <div style={{ display: "flex", gap: "0.5rem", margin: "0.5rem 0" }}>
        <select value={bankType} onChange={(e) => setBankType(e.target.value)}>
          {BANK_TYPES.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        <input
          dir="auto"
          placeholder="verbatim phrase (stored exactly)"
          style={{ flex: 1, padding: "0.5rem" }}
          value={phrase}
          onChange={(e) => setPhrase(e.target.value)}
        />
        <button onClick={add}>Add</button>
        <button onClick={refresh}>Refresh</button>
      </div>
      {err && <p style={{ color: "crimson" }}>{err}</p>}

      <h3>Language banks</h3>
      <ul>
        {banks.map((b) => (
          <li key={b.bank_type} dir="auto">
            <strong>{b.bank_type}</strong>: {b.phrase_count} phrases · {b.approved_count} approved · confidence{" "}
            <em>{b.confidence}</em> · {b.confirmed_patterns.length} confirmed pattern(s)
          </li>
        ))}
      </ul>

      <h3>Entries</h3>
      <ul>
        {entries.map((e) => (
          <li key={e.id} dir="auto" style={{ margin: "0.4rem 0" }}>
            <blockquote dir="auto" style={{ margin: 0 }}>
              {e.verbatim_phrase}
            </blockquote>
            <small>
              [{e.bank_type} · ×{e.occurrence_count} · {e.review_status}]
            </small>{" "}
            {e.review_status !== "approved" && <button onClick={() => approve(e.id)}>Approve</button>}
          </li>
        ))}
      </ul>
    </section>
  );
}
