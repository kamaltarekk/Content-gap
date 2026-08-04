import { useState } from "react";
import { apiGet, apiPost, apiPut } from "../api/client";

interface CostSummary {
  total_cost_usd: number;
  budget_cap_usd: number | null;
  call_count: number;
  cache_hits: number;
  entries: { task: string; model: string; cost_usd: number; cache_hit: boolean }[];
}

// Cost & operations panel: shows the cost ledger (with cache status), lets you set a budget cap,
// preview PII redaction before upload, and purge a project's raw + derived data.
export default function CostOps() {
  const [projectId, setProjectId] = useState("");
  const [cost, setCost] = useState<CostSummary | null>(null);
  const [cap, setCap] = useState("");
  const [pii, setPii] = useState("");
  const [preview, setPreview] = useState<{ has_pii: boolean; found: { emails: number; phones: number }; preview: string } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function loadCost() {
    setMsg(null);
    try {
      setCost(await apiGet<CostSummary>(`/api/v1/projects/${projectId}/cost`));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    }
  }
  async function saveCap() {
    await apiPut(`/api/v1/projects/${projectId}/budget-cap`, { budget_cap_usd: cap === "" ? null : Number(cap) });
    await loadCost();
  }
  async function runPreview() {
    setPreview(await apiPost(`/api/v1/pii/redaction-preview`, { text: pii }));
  }
  async function purge() {
    if (!confirm("Purge removes ALL raw and derived data for this project. Continue?")) return;
    const r = await apiPost<{ content_pieces: number }>(`/api/v1/projects/${projectId}/purge`, {});
    setMsg(`Purged. Removed ${r.content_pieces} content piece(s).`);
    setCost(null);
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 820, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Cost &amp; operations — التكلفة والتشغيل</h2>
      <input
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.5rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button onClick={loadCost}>Load cost ledger</button>
        <input placeholder="budget cap (USD)" value={cap} onChange={(e) => setCap(e.target.value)} />
        <button onClick={saveCap}>Set cap</button>
        <button onClick={purge} style={{ color: "crimson" }}>Purge project</button>
      </div>
      {msg && <p>{msg}</p>}

      {cost && (
        <>
          <p>
            Total: <strong>${cost.total_cost_usd}</strong> · cap:{" "}
            {cost.budget_cap_usd === null ? "none" : `$${cost.budget_cap_usd}`} · calls {cost.call_count} · cache hits{" "}
            {cost.cache_hits}
          </p>
          <ul>
            {cost.entries.map((e, i) => (
              <li key={i}>
                {e.task} · {e.model} · ${e.cost_usd} {e.cache_hit ? "(cache)" : ""}
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>PII redaction preview</h3>
      <textarea
        dir="auto"
        placeholder="paste CSV / manual text to preview redaction before upload"
        style={{ width: "100%", minHeight: 80 }}
        value={pii}
        onChange={(e) => setPii(e.target.value)}
      />
      <button onClick={runPreview}>Preview redaction</button>
      {preview && (
        <div dir="auto">
          <p>
            PII found: {preview.found.emails} email(s), {preview.found.phones} phone(s)
          </p>
          <pre style={{ whiteSpace: "pre-wrap", background: "#f5f5f5", padding: "0.5rem" }}>{preview.preview}</pre>
        </div>
      )}
    </section>
  );
}
