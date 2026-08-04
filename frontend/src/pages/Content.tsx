import { useState } from "react";
import { apiGet } from "../api/client";

interface Piece {
  id: string;
  content_format: string;
  language_code: string;
  title: string | null;
  original_text: string;
  normalized_text: string;
  is_canonical: boolean;
  source_snapshot_id: string;
}
interface Span {
  id: string;
  span_type: string;
  quoted_text: string;
}
interface SourceContext {
  source_snapshot_id: string;
  source_id: string | null;
  surrounding_text: string;
}

// Minimal content inventory: list pieces for a project, open a piece's evidence span, and trace
// it to the exact source snapshot (the Phase 3 gate, exercised from the UI).
export default function Content() {
  const [projectId, setProjectId] = useState("");
  const [pieces, setPieces] = useState<Piece[]>([]);
  const [spans, setSpans] = useState<Span[]>([]);
  const [ctx, setCtx] = useState<SourceContext | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setErr(null);
    setCtx(null);
    setSpans([]);
    try {
      setPieces(await apiGet<Piece[]>(`/api/v1/projects/${projectId}/content`));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }
  async function openPiece(id: string) {
    const s = await apiGet<Span[]>(`/api/v1/content/${id}/evidence`);
    setSpans(s);
    if (s[0]) setCtx(await apiGet<SourceContext>(`/api/v1/evidence/${s[0].id}/source-context`));
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 820, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Content inventory — مخزون المحتوى</h2>
      <input
        dir="auto"
        placeholder="project id"
        style={{ width: "100%", padding: "0.5rem", margin: "0.5rem 0" }}
        value={projectId}
        onChange={(e) => setProjectId(e.target.value)}
      />
      <button onClick={load}>Load content</button>
      {err && <p style={{ color: "crimson" }}>{err}</p>}
      <ul>
        {pieces.map((p) => (
          <li key={p.id} dir="auto" style={{ margin: "0.5rem 0" }}>
            <button onClick={() => openPiece(p.id)}>[{p.content_format} · {p.language_code} · {p.is_canonical ? "canonical" : "duplicate"}]</button>{" "}
            {p.original_text.slice(0, 60)}
          </li>
        ))}
      </ul>
      {spans[0] && (
        <div dir="auto" style={{ borderTop: "1px solid #ccc", paddingTop: "1rem" }}>
          <h3>Evidence span ({spans[0].span_type})</h3>
          <blockquote dir="auto">{spans[0].quoted_text}</blockquote>
          {ctx && (
            <p>Traced to source snapshot <code>{ctx.source_snapshot_id}</code> (source <code>{ctx.source_id}</code>).</p>
          )}
        </div>
      )}
    </section>
  );
}
