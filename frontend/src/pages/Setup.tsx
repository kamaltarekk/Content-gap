import { useState } from "react";
import { apiPost } from "../api/client";

interface GateResult {
  status: string;
  missing_required_fields: string[];
  warnings: string[];
  can_run_full_analysis: boolean;
  can_run_partial_analysis: boolean;
}

// Minimal context-setup flow: create project → add primary brand → create a diagnostic context
// version → validate against the prerequisite gate. Full analysis stays blocked until the gate
// passes (severity/readiness are never produced here). Arabic-first, dir="auto" throughout.
export default function Setup() {
  const [projectName, setProjectName] = useState("مشروع نقاء");
  const [brandName, setBrandName] = useState("نقاء");
  const [decision, setDecision] = useState("شراء أول فلتر مياه منزلي");
  const [segment, setSegment] = useState("أسر حضرية مهتمة بالصحة");
  const [gate, setGate] = useState<GateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    setGate(null);
    try {
      const project = await apiPost<{ id: string }>("/api/v1/projects", { name: projectName, primary_language: "ar" });
      await apiPost(`/api/v1/projects/${project.id}/entities`, { entity_type: "brand", name: brandName });
      const ctx = await apiPost<{ id: string }>(`/api/v1/projects/${project.id}/context/versions`, {
        target_buying_decision: decision,
        purchase_type: "first_purchase",
        primary_product_or_service: "منتج/خدمة",
        primary_segment_name: segment,
        primary_segment_definition: segment,
        primary_decision_maker_role: "parent_caregiver",
        primary_bottleneck: "persuasion",
        bottleneck_statement: "سبب العائق",
        included_channels: ["instagram", "website"],
      });
      const result = await apiPost<GateResult>(`/api/v1/context/versions/${ctx.id}/validate`, {});
      setGate(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  const field = { display: "block", width: "100%", padding: "0.5rem", margin: "0.25rem 0 1rem" } as const;

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>إعداد سياق التشخيص — Diagnostic Context Setup</h2>
      <label>Project name<input dir="auto" style={field} value={projectName} onChange={(e) => setProjectName(e.target.value)} /></label>
      <label>Primary brand<input dir="auto" style={field} value={brandName} onChange={(e) => setBrandName(e.target.value)} /></label>
      <label>Target buying decision<input dir="auto" style={field} value={decision} onChange={(e) => setDecision(e.target.value)} /></label>
      <label>Primary segment<input dir="auto" style={field} value={segment} onChange={(e) => setSegment(e.target.value)} /></label>
      <button disabled={busy} onClick={run}>{busy ? "…" : "Create & validate"}</button>

      {error && <p style={{ color: "crimson" }}>Backend not reachable or error: {error}</p>}
      {gate && (
        <div style={{ marginTop: "1.5rem" }}>
          <p>Gate status: <strong>{gate.status}</strong></p>
          <p>Full analysis allowed: <strong>{String(gate.can_run_full_analysis)}</strong> · Partial: {String(gate.can_run_partial_analysis)}</p>
          {gate.missing_required_fields.length > 0 && (
            <p dir="auto">Missing: {gate.missing_required_fields.join(", ")}</p>
          )}
          {gate.warnings.map((w) => (
            <p key={w} dir="auto" style={{ color: "#a60" }}>⚠ {w}</p>
          ))}
        </div>
      )}
    </section>
  );
}
