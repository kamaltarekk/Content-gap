import { type AppConfig, domainOf } from "@cgi/shared";
import { extractFromHtml, normalizeText, type ExtractedPage } from "./extract.js";
import { PerDomainRateLimiter } from "./rate-limiter.js";
import { RobotsCache } from "./robots.js";

export interface FetchResult {
  ok: boolean;
  status: number;
  title: string;
  text: string;
  method: string;
  error?: string;
}

/**
 * Public-content fetcher. HTTP first; Playwright only as an explicit, opt-in fallback for
 * JS-rendered pages. Never bypasses auth/CAPTCHA/paywalls/rate limits. Respects robots.txt.
 */
export class Fetcher {
  private limiter: PerDomainRateLimiter;
  private robots: RobotsCache;
  constructor(
    private config: AppConfig,
    private fetchImpl: typeof fetch = fetch,
  ) {
    this.limiter = new PerDomainRateLimiter(config.crawler.perDomainRps);
    this.robots = new RobotsCache(config.crawler.userAgent, fetchImpl, config.crawler.respectRobots);
  }

  async fetchUrl(url: string): Promise<FetchResult> {
    const allowed = await this.robots.isAllowed(url);
    if (!allowed) {
      return { ok: false, status: 0, title: "", text: "", method: "robots", error: "Disallowed by robots.txt" };
    }
    await this.limiter.acquire(domainOf(url));
    try {
      const res = await this.fetchImpl(url, {
        headers: { "user-agent": this.config.crawler.userAgent, accept: "text/html,text/plain" },
        redirect: "follow",
      });
      const contentType = res.headers.get("content-type") ?? "";
      const bodyText = await res.text();
      if (bodyText.length > this.config.limits.maxPageBytes) {
        return { ok: false, status: res.status, title: "", text: "", method: "http", error: "Page exceeds max size" };
      }
      if (!res.ok) {
        return { ok: false, status: res.status, title: "", text: "", method: "http", error: `HTTP ${res.status}` };
      }
      let page: ExtractedPage;
      if (contentType.includes("html")) page = extractFromHtml(bodyText, url);
      else page = { title: "", text: normalizeText(bodyText), method: "cheerio" };

      // Opt-in Playwright fallback for thin JS-rendered pages.
      if (page.text.trim().length < 120 && this.config.crawler.playwrightFallback) {
        const rendered = await this.tryPlaywright(url);
        if (rendered) page = rendered;
      }
      return { ok: true, status: res.status, title: page.title, text: page.text, method: page.method };
    } catch (err) {
      return { ok: false, status: 0, title: "", text: "", method: "http", error: (err as Error).message };
    }
  }

  private async tryPlaywright(url: string): Promise<ExtractedPage | null> {
    try {
      // Dynamically imported (optional dep) so Playwright is not required to build/run.
      const specifier = "playwright";
      const mod: any = await import(specifier).catch(() => null);
      if (!mod?.chromium) return null;
      const browser = await mod.chromium.launch();
      try {
        const page = await browser.newPage({ userAgent: this.config.crawler.userAgent });
        await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
        const html = await page.content();
        return extractFromHtml(html, url);
      } finally {
        await browser.close();
      }
    } catch {
      return null;
    }
  }
}
