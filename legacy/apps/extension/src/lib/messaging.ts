// Shared message contract between the side panel UI and the background service worker.
// The background worker owns all network access and tab scripting; the UI only sends
// typed requests. Auth (backendUrl + projectToken) lives in chrome.storage.local.

export type BgRequest =
  | { type: "testConnection"; backendUrl: string; projectToken: string }
  | { type: "capture" }
  | { type: "apiFetch"; method: string; path: string; body?: unknown };

export interface TestConnectionResult {
  projectId: string;
  projectName: string | null;
}

export interface CaptureResult {
  title: string;
  url: string;
  text: string;
}

export interface ApiFetchResult {
  status: number;
  data: unknown;
}

export type Ok<T> = { ok: true } & T;
export type Err = { ok: false; error: string };
export type Result<T> = Ok<T> | Err;

export function sendMessage<T>(req: BgRequest): Promise<Result<T>> {
  return chrome.runtime.sendMessage(req) as Promise<Result<T>>;
}
