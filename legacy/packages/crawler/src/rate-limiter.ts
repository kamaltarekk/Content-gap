// Per-domain token-bucket rate limiter. Deterministic policy; uses injectable now()/sleep for tests.

export interface Clock {
  now(): number;
  sleep(ms: number): Promise<void>;
}

export const realClock: Clock = {
  now: () => Date.now(),
  sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
};

export class PerDomainRateLimiter {
  private nextAllowed = new Map<string, number>();
  private readonly minIntervalMs: number;
  constructor(perDomainRps: number, private clock: Clock = realClock) {
    this.minIntervalMs = perDomainRps > 0 ? Math.ceil(1000 / perDomainRps) : 0;
  }

  async acquire(domain: string): Promise<void> {
    if (this.minIntervalMs === 0) return;
    const now = this.clock.now();
    const earliest = this.nextAllowed.get(domain) ?? 0;
    const waitMs = Math.max(0, earliest - now);
    if (waitMs > 0) await this.clock.sleep(waitMs);
    this.nextAllowed.set(domain, this.clock.now() + this.minIntervalMs);
  }
}
