// `defineBackground` is a WXT auto-import (injected at build by the unimport plugin). Importing
// it explicitly from "wxt/client" makes vite-node externalize a virtual module and fail on Node's
// ESM loader, so we rely on the auto-import and declare its type locally (erased at build).
declare function defineBackground(main: () => void | Promise<void>): void;
import type {
  ApiFetchResult,
  BgRequest,
  CaptureResult,
  Result,
  TestConnectionResult,
} from "../lib/messaging";

interface StoredAuth {
  backendUrl?: string;
  projectToken?: string;
}

async function getAuth(): Promise<StoredAuth> {
  const data = await chrome.storage.local.get(["backendUrl", "projectToken"]);
  return {
    backendUrl: typeof data.backendUrl === "string" ? data.backendUrl : undefined,
    projectToken: typeof data.projectToken === "string" ? data.projectToken : undefined,
  };
}

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

async function touchLastSync(): Promise<void> {
  await chrome.storage.local.set({ lastSyncAt: Date.now() });
}

async function testConnection(
  backendUrl: string,
  projectToken: string,
): Promise<Result<TestConnectionResult>> {
  const res = await fetch(joinUrl(backendUrl, "/api/v1/me"), {
    headers: { Authorization: `Bearer ${projectToken}` },
  });
  if (!res.ok) {
    return { ok: false, error: `Connection failed (HTTP ${res.status})` };
  }
  const data = (await res.json()) as { projectId?: string; projectName?: string | null };
  if (!data.projectId) {
    return { ok: false, error: "Response missing projectId" };
  }
  await chrome.storage.local.set({
    backendUrl,
    projectToken,
    projectId: data.projectId,
    projectName: data.projectName ?? null,
  });
  await touchLastSync();
  return { ok: true, projectId: data.projectId, projectName: data.projectName ?? null };
}

async function captureActiveTab(): Promise<Result<CaptureResult>> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    return { ok: false, error: "No active tab found" };
  }
  const injection = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => ({
      title: document.title,
      url: location.href,
      text: document.body?.innerText ?? "",
    }),
  });
  const result = injection[0]?.result;
  if (!result) {
    return { ok: false, error: "Could not read the page (permission may be missing)" };
  }
  return { ok: true, title: result.title, url: result.url, text: result.text };
}

async function apiFetch(
  method: string,
  path: string,
  body: unknown,
): Promise<Result<ApiFetchResult>> {
  const { backendUrl, projectToken } = await getAuth();
  if (!backendUrl || !projectToken) {
    return { ok: false, error: "Not connected. Set backend URL and token first." };
  }
  const res = await fetch(joinUrl(backendUrl, path), {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${projectToken}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data: unknown = await res.json().catch(() => null);
  await touchLastSync();
  return { ok: true, status: res.status, data };
}

async function handle(req: BgRequest): Promise<Result<unknown>> {
  switch (req.type) {
    case "testConnection":
      return testConnection(req.backendUrl, req.projectToken);
    case "capture":
      return captureActiveTab();
    case "apiFetch":
      return apiFetch(req.method, req.path, req.body);
    default:
      return { ok: false, error: "Unknown request" };
  }
}

export default defineBackground(() => {
  // Open the side panel when the toolbar action is clicked.
  void chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch(() => undefined);

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    handle(message as BgRequest)
      .then(sendResponse)
      .catch((err: unknown) => {
        const error = err instanceof Error ? err.message : String(err);
        sendResponse({ ok: false, error });
      });
    // Keep the message channel open for the async response.
    return true;
  });
});
