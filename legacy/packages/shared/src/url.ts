// Deterministic URL normalization. Same logical page -> same canonical URL, so
// snapshots and dedup are stable. No network access.

const TRACKING_PARAMS = new Set([
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_term",
  "utm_content",
  "gclid",
  "fbclid",
  "mc_cid",
  "mc_eid",
  "ref",
  "ref_src",
]);

export function normalizeUrl(input: string): string {
  const url = new URL(input.trim());
  url.protocol = url.protocol.toLowerCase();
  url.hostname = url.hostname.toLowerCase();
  url.hash = "";

  // Drop default ports.
  if ((url.protocol === "http:" && url.port === "80") || (url.protocol === "https:" && url.port === "443")) {
    url.port = "";
  }

  // Remove tracking params, keep the rest, sort for stability.
  const params = [...url.searchParams.entries()].filter(([k]) => !TRACKING_PARAMS.has(k.toLowerCase()));
  params.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  url.search = "";
  for (const [k, v] of params) url.searchParams.append(k, v);

  // Normalize path: collapse duplicate slashes, drop trailing slash (except root).
  let path = url.pathname.replace(/\/{2,}/g, "/");
  if (path.length > 1 && path.endsWith("/")) path = path.slice(0, -1);
  url.pathname = path;

  return url.toString();
}

/** Registrable-ish domain for ownership + per-domain rate limiting (host without leading www). */
export function domainOf(input: string): string {
  const host = new URL(input.trim()).hostname.toLowerCase();
  return host.startsWith("www.") ? host.slice(4) : host;
}

export function isValidHttpUrl(input: string): boolean {
  try {
    const u = new URL(input.trim());
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}
