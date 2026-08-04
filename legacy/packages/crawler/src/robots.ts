// Minimal robots.txt parser. Fetches and caches per-origin rules for our user agent.
// Conservative: on fetch error we do NOT assume disallow (public content), but we record it.

interface RobotsRules {
  disallow: string[];
  allow: string[];
}

export class RobotsCache {
  private cache = new Map<string, RobotsRules>();
  constructor(
    private userAgent: string,
    private fetchImpl: typeof fetch = fetch,
    private enabled = true,
  ) {}

  async isAllowed(url: string): Promise<boolean> {
    if (!this.enabled) return true;
    const u = new URL(url);
    const origin = u.origin;
    let rules = this.cache.get(origin);
    if (!rules) {
      rules = await this.load(origin);
      this.cache.set(origin, rules);
    }
    const path = u.pathname;
    const matchLen = (patterns: string[]) =>
      patterns.filter((p) => path.startsWith(p)).reduce((max, p) => Math.max(max, p.length), -1);
    const dis = matchLen(rules.disallow);
    const allow = matchLen(rules.allow);
    if (dis < 0) return true;
    return allow >= dis; // most-specific rule wins; ties favor allow
  }

  private async load(origin: string): Promise<RobotsRules> {
    const rules: RobotsRules = { disallow: [], allow: [] };
    try {
      const res = await this.fetchImpl(`${origin}/robots.txt`, {
        headers: { "user-agent": this.userAgent },
      });
      if (!res.ok) return rules;
      const text = await res.text();
      let applies = false;
      for (const line of text.split(/\r?\n/)) {
        const clean = line.replace(/#.*$/, "").trim();
        if (!clean) continue;
        const [rawKey, ...rest] = clean.split(":");
        const key = rawKey?.toLowerCase().trim();
        const value = rest.join(":").trim();
        if (key === "user-agent") {
          applies = value === "*" || value.toLowerCase() === this.userAgent.toLowerCase();
        } else if (applies && key === "disallow" && value) {
          rules.disallow.push(value);
        } else if (applies && key === "allow" && value) {
          rules.allow.push(value);
        }
      }
    } catch {
      // network failure: leave rules empty (allowed), caller records source status separately
    }
    return rules;
  }
}
