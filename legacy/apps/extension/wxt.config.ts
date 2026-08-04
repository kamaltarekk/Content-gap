import { defineConfig } from "wxt";

// Content Gap Intelligence — Chrome Side Panel extension (Manifest V3).
// Minimal permissions: no <all_urls>, no auto-injected content scripts, no Anthropic key.
// Host access is requested at runtime per user-approved domain when capturing a page.
export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  srcDir: "src",
  manifest: {
    name: "Content Gap Intelligence",
    description: "Capture pages and review content gaps from the CGI backend.",
    permissions: ["sidePanel", "storage", "activeTab", "scripting"],
    optional_host_permissions: ["https://*/*", "http://*/*"],
    action: {
      default_title: "Content Gap Intelligence",
    },
    side_panel: {
      default_path: "sidepanel.html",
    },
  },
});
