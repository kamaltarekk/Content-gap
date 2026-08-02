# @cgi/extension

Chrome Manifest V3 side-panel extension for **Content Gap Intelligence** (WXT + React + TypeScript).

It connects to the CGI backend with a project token, lets you capture the current page
on demand, and review content gaps and source status — all from the Chrome Side Panel.

## Privacy / permissions

- Permissions are minimal: `sidePanel`, `storage`, `activeTab`, `scripting`.
- **No** `<all_urls>` and no auto-injected content scripts. A page is only read when you
  click **Capture current page**, and the extension requests host access for that one
  domain at that moment (`optional_host_permissions` + `chrome.permissions.request`).
- Browsing history is never captured.
- The extension never holds an Anthropic API key — only the backend URL and a project
  bearer token (stored in `chrome.storage.local`).

## Develop

```bash
pnpm --filter @cgi/extension dev
```

## Build

```bash
pnpm --filter @cgi/extension build
```

## Load in Chrome

1. Run the build (or `dev`) command above.
2. Open `chrome://extensions`.
3. Enable **Developer mode** (top-right).
4. Click **Load unpacked** and select the build output:
   `apps/extension/.output/chrome-mv3`.
5. Click the extension's toolbar icon to open the side panel.

## Views

1. **Connection** — set backend URL (default `http://localhost:3001`) and project token,
   then **Test connection** (`GET /api/v1/me`). Shows the connected project and last sync.
2. **Capture** — pick source ownership (Owned / Competitor 1–3 / Voice of Customer),
   capture the current page, preview it, and submit
   (`POST /api/v1/projects/{projectId}/sources/capture`).
3. **Gaps** — top gaps from `GET /api/v1/projects/{projectId}/gaps`, each linking to the
   dashboard gap detail (`http://localhost:5173/#/gap/{id}`).
4. **Sources** — counts and lists for pending / processed / failed / needs-attention from
   `GET /api/v1/projects/{projectId}/sources`.
