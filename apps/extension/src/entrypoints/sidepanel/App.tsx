import { useCallback, useEffect, useState } from "react";
import {
  OWNER_OPTIONS,
  type Gap,
  type OwnerOption,
  type SourcesResponse,
} from "../../lib/api";
import {
  sendMessage,
  type ApiFetchResult,
  type CaptureResult,
  type TestConnectionResult,
} from "../../lib/messaging";

const DEFAULT_BACKEND = "http://localhost:3001";
const DASHBOARD_BASE = "http://localhost:5173";

type Tab = "connection" | "capture" | "gaps" | "sources";

const TABS: { id: Tab; label: string }[] = [
  { id: "connection", label: "Connection" },
  { id: "capture", label: "Capture" },
  { id: "gaps", label: "Gaps" },
  { id: "sources", label: "Sources" },
];

// ---- shared styles ----
const S = {
  page: { fontFamily: "system-ui, sans-serif", fontSize: 13, color: "#1a1a1a", padding: 12 } as const,
  tabs: { display: "flex", gap: 4, borderBottom: "1px solid #ddd", marginBottom: 12 } as const,
  tabBtn: (active: boolean) =>
    ({
      flex: 1,
      padding: "6px 4px",
      border: "none",
      borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
      background: "none",
      color: active ? "#2563eb" : "#555",
      fontWeight: active ? 600 : 400,
      cursor: "pointer",
    }) as const,
  label: { display: "block", fontWeight: 600, margin: "8px 0 2px" } as const,
  input: { width: "100%", padding: "6px 8px", boxSizing: "border-box", border: "1px solid #ccc", borderRadius: 4 } as const,
  button: {
    marginTop: 10,
    padding: "8px 12px",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
  } as const,
  buttonDisabled: { opacity: 0.5, cursor: "not-allowed" } as const,
  card: { border: "1px solid #e5e5e5", borderRadius: 6, padding: 10, marginBottom: 8 } as const,
  ok: { color: "#15803d" } as const,
  err: { color: "#b91c1c" } as const,
  muted: { color: "#777" } as const,
  badge: { display: "inline-block", padding: "1px 6px", borderRadius: 4, background: "#eef", fontSize: 11, marginRight: 4 } as const,
};

function useStorage() {
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND);
  const [projectToken, setProjectToken] = useState("");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    void chrome.storage.local
      .get(["backendUrl", "projectToken", "projectId", "projectName", "lastSyncAt"])
      .then((d) => {
        if (typeof d.backendUrl === "string") setBackendUrl(d.backendUrl);
        if (typeof d.projectToken === "string") setProjectToken(d.projectToken);
        if (typeof d.projectId === "string") setProjectId(d.projectId);
        if (typeof d.projectName === "string") setProjectName(d.projectName);
        if (typeof d.lastSyncAt === "number") setLastSyncAt(d.lastSyncAt);
        setLoaded(true);
      });
    const listener = (changes: Record<string, chrome.storage.StorageChange>, area: string) => {
      if (area !== "local") return;
      if (changes.lastSyncAt && typeof changes.lastSyncAt.newValue === "number") {
        setLastSyncAt(changes.lastSyncAt.newValue);
      }
    };
    chrome.storage.onChanged.addListener(listener);
    return () => chrome.storage.onChanged.removeListener(listener);
  }, []);

  return {
    backendUrl, setBackendUrl,
    projectToken, setProjectToken,
    projectId, setProjectId,
    projectName, setProjectName,
    lastSyncAt, setLastSyncAt,
    loaded,
  };
}

type Store = ReturnType<typeof useStorage>;

export function App() {
  const store = useStorage();
  const [tab, setTab] = useState<Tab>("connection");

  return (
    <div style={S.page}>
      <div style={S.tabs}>
        {TABS.map((t) => (
          <button key={t.id} style={S.tabBtn(tab === t.id)} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "connection" && <ConnectionView store={store} />}
      {tab === "capture" && <CaptureView store={store} />}
      {tab === "gaps" && <GapsView store={store} />}
      {tab === "sources" && <SourcesView store={store} />}
    </div>
  );
}

function LastSync({ at }: { at: number | null }) {
  if (!at) return null;
  return <p style={S.muted}>Last sync: {new Date(at).toLocaleString()}</p>;
}

// ---- 1. Connection ----
function ConnectionView({ store }: { store: Store }) {
  const [status, setStatus] = useState<"idle" | "testing">("idle");
  const [error, setError] = useState<string | null>(null);

  const test = useCallback(async () => {
    setStatus("testing");
    setError(null);
    const res = await sendMessage<TestConnectionResult>({
      type: "testConnection",
      backendUrl: store.backendUrl,
      projectToken: store.projectToken,
    });
    setStatus("idle");
    if (res.ok) {
      store.setProjectId(res.projectId);
      store.setProjectName(res.projectName);
    } else {
      setError(res.error);
    }
  }, [store]);

  return (
    <div>
      <label style={S.label}>Backend URL</label>
      <input
        style={S.input}
        value={store.backendUrl}
        placeholder={DEFAULT_BACKEND}
        onChange={(e) => store.setBackendUrl(e.target.value)}
      />
      <label style={S.label}>Project token</label>
      <input
        style={S.input}
        type="password"
        value={store.projectToken}
        placeholder="Bearer token"
        onChange={(e) => store.setProjectToken(e.target.value)}
      />
      <button
        style={{ ...S.button, ...(status === "testing" ? S.buttonDisabled : {}) }}
        disabled={status === "testing"}
        onClick={() => void test()}
      >
        {status === "testing" ? "Testing…" : "Test connection"}
      </button>

      {store.projectId && !error && (
        <div style={{ ...S.card, marginTop: 12 }}>
          <div style={S.ok}>Connected</div>
          <div>Project: {store.projectName ?? "(unnamed)"}</div>
          <div style={S.muted}>ID: {store.projectId}</div>
        </div>
      )}
      {error && <p style={S.err}>Error: {error}</p>}
      <LastSync at={store.lastSyncAt} />
    </div>
  );
}

// ---- 2. Capture ----
async function ensureHostPermission(): Promise<{ ok: boolean; error?: string }> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return { ok: false, error: "No active tab" };
  try {
    const u = new URL(tab.url);
    if (u.protocol !== "http:" && u.protocol !== "https:") {
      return { ok: false, error: "This page type cannot be captured" };
    }
    const origin = `${u.protocol}//${u.hostname}/*`;
    const has = await chrome.permissions.contains({ origins: [origin] });
    if (has) return { ok: true };
    const granted = await chrome.permissions.request({ origins: [origin] });
    return granted ? { ok: true } : { ok: false, error: "Host permission denied" };
  } catch {
    return { ok: false, error: "Invalid page URL" };
  }
}

function CaptureView({ store }: { store: Store }) {
  const [ownerIdx, setOwnerIdx] = useState(0);
  const [preview, setPreview] = useState<CaptureResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const owner: OwnerOption = OWNER_OPTIONS[ownerIdx] ?? OWNER_OPTIONS[0]!;

  const capture = useCallback(async () => {
    setBusy(true);
    setMessage(null);
    setPreview(null);
    const perm = await ensureHostPermission();
    if (!perm.ok) {
      setBusy(false);
      setMessage({ kind: "err", text: perm.error ?? "Permission error" });
      return;
    }
    const res = await sendMessage<CaptureResult>({ type: "capture" });
    setBusy(false);
    if (res.ok) {
      setPreview({ title: res.title, url: res.url, text: res.text });
    } else {
      setMessage({ kind: "err", text: res.error });
    }
  }, []);

  const submit = useCallback(async () => {
    if (!preview) return;
    if (!store.projectId) {
      setMessage({ kind: "err", text: "Not connected — test connection first." });
      return;
    }
    setBusy(true);
    setMessage(null);
    const res = await sendMessage<ApiFetchResult>({
      type: "apiFetch",
      method: "POST",
      path: `/api/v1/projects/${store.projectId}/sources/capture`,
      body: {
        ownerType: owner.ownerType,
        competitorSlot: owner.competitorSlot,
        url: preview.url,
        title: preview.title,
        text: preview.text,
      },
    });
    setBusy(false);
    if (res.ok && res.status >= 200 && res.status < 300) {
      setMessage({ kind: "ok", text: "Captured and submitted." });
      setPreview(null);
    } else if (res.ok) {
      setMessage({ kind: "err", text: `Submit failed (HTTP ${res.status})` });
    } else {
      setMessage({ kind: "err", text: res.error });
    }
  }, [preview, owner, store.projectId]);

  return (
    <div>
      <label style={S.label}>Source ownership</label>
      <select style={S.input} value={ownerIdx} onChange={(e) => setOwnerIdx(Number(e.target.value))}>
        {OWNER_OPTIONS.map((o, i) => (
          <option key={o.label} value={i}>
            {o.label}
          </option>
        ))}
      </select>
      <button
        style={{ ...S.button, ...(busy ? S.buttonDisabled : {}) }}
        disabled={busy}
        onClick={() => void capture()}
      >
        Capture current page
      </button>

      {preview && (
        <div style={{ ...S.card, marginTop: 12 }}>
          <div><strong>{preview.title || "(no title)"}</strong></div>
          <div style={S.muted}>{preview.url}</div>
          <div style={S.muted}>{preview.text.length.toLocaleString()} characters extracted</div>
          <button
            style={{ ...S.button, ...(busy ? S.buttonDisabled : {}) }}
            disabled={busy}
            onClick={() => void submit()}
          >
            Submit
          </button>
        </div>
      )}
      {message && <p style={message.kind === "ok" ? S.ok : S.err}>{message.text}</p>}
      <LastSync at={store.lastSyncAt} />
    </div>
  );
}

// ---- 3. Gaps ----
function GapsView({ store }: { store: Store }) {
  const [gaps, setGaps] = useState<Gap[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!store.projectId) {
      setError("Not connected — test connection first.");
      return;
    }
    setLoading(true);
    setError(null);
    const res = await sendMessage<ApiFetchResult>({
      type: "apiFetch",
      method: "GET",
      path: `/api/v1/projects/${store.projectId}/gaps`,
    });
    setLoading(false);
    if (res.ok && res.status >= 200 && res.status < 300 && Array.isArray(res.data)) {
      setGaps(res.data as Gap[]);
    } else if (res.ok) {
      setError(`Failed to load gaps (HTTP ${res.status})`);
    } else {
      setError(res.error);
    }
  }, [store.projectId]);

  const openGap = (id: string) => {
    void chrome.tabs.create({ url: `${DASHBOARD_BASE}/#/gap/${id}` });
  };

  return (
    <div>
      <button
        style={{ ...S.button, marginTop: 0, ...(loading ? S.buttonDisabled : {}) }}
        disabled={loading}
        onClick={() => void load()}
      >
        {loading ? "Loading…" : "Load gaps"}
      </button>
      {error && <p style={S.err}>{error}</p>}
      {gaps && gaps.length === 0 && <p style={S.muted}>No gaps found.</p>}
      <div style={{ marginTop: 10 }}>
        {gaps?.map((g) => (
          <div key={g.id} style={S.card}>
            <div>
              <span style={S.badge}>{g.gapType}</span>
              <span style={S.badge}>{g.priorityLabel}</span>
            </div>
            <div style={{ fontWeight: 600, margin: "4px 0" }}>{g.title}</div>
            <div style={S.muted}>Cohort: {g.cohortId ?? "—"}</div>
            <div style={S.muted}>Stage: {g.journeyStage} · Evidence: {g.evidenceStatus}</div>
            {g.rankingReason && <div style={{ marginTop: 4 }}>{g.rankingReason}</div>}
            <a
              href={`${DASHBOARD_BASE}/#/gap/${g.id}`}
              onClick={(e) => {
                e.preventDefault();
                openGap(g.id);
              }}
              style={{ color: "#2563eb", cursor: "pointer" }}
            >
              Open in dashboard →
            </a>
          </div>
        ))}
      </div>
      <LastSync at={store.lastSyncAt} />
    </div>
  );
}

// ---- 4. Source status ----
function SourceList({ title, items }: { title: string; items: SourcesResponse["all"] }) {
  return (
    <div style={S.card}>
      <div style={{ fontWeight: 600 }}>
        {title} ({items.length})
      </div>
      {items.map((s) => (
        <div key={s.id} style={S.muted}>
          {s.name} · {s.ownerType} · {s.status}
        </div>
      ))}
    </div>
  );
}

function SourcesView({ store }: { store: Store }) {
  const [data, setData] = useState<SourcesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!store.projectId) {
      setError("Not connected — test connection first.");
      return;
    }
    setLoading(true);
    setError(null);
    const res = await sendMessage<ApiFetchResult>({
      type: "apiFetch",
      method: "GET",
      path: `/api/v1/projects/${store.projectId}/sources`,
    });
    setLoading(false);
    if (res.ok && res.status >= 200 && res.status < 300 && res.data) {
      setData(res.data as SourcesResponse);
    } else if (res.ok) {
      setError(`Failed to load sources (HTTP ${res.status})`);
    } else {
      setError(res.error);
    }
  }, [store.projectId]);

  return (
    <div>
      <button
        style={{ ...S.button, marginTop: 0, ...(loading ? S.buttonDisabled : {}) }}
        disabled={loading}
        onClick={() => void load()}
      >
        {loading ? "Loading…" : "Load sources"}
      </button>
      {error && <p style={S.err}>{error}</p>}
      {data && (
        <div style={{ marginTop: 10 }}>
          <SourceList title="Pending" items={data.pending} />
          <SourceList title="Processed" items={data.processed} />
          <SourceList title="Failed" items={data.failed} />
          <SourceList title="Needs attention" items={data.needsAttention} />
        </div>
      )}
      <LastSync at={store.lastSyncAt} />
    </div>
  );
}
