import type { Request, Response, NextFunction } from "express";

interface CircuitBreakerConfig {
  threshold: number;
  cooldownMs: number;
}

class CircuitBreaker {
  private failures = 0;
  private tripped = false;
  private trippedAt = 0;

  constructor(private config: CircuitBreakerConfig) {}

  recordFailure(): void {
    this.failures++;
    if (this.failures >= this.config.threshold && !this.tripped) {
      this.tripped = true;
      this.trippedAt = Date.now();
    }
  }

  recordSuccess(): void {
    this.failures = 0;
    this.tripped = false;
    this.trippedAt = 0;
  }

  isOpen(): boolean {
    if (!this.tripped) return false;
    return Date.now() - this.trippedAt < this.config.cooldownMs;
  }

  status() {
    return { failures: this.failures, tripped: this.tripped };
  }
}

interface BudgetConfig { dailyLimitUsd: number; }

class BudgetTracker {
  private spentUsd = 0;
  private dayStart = Date.now();

  constructor(private config: BudgetConfig) {}

  recordRevenue(amountUsd: number): void {
    this.maybeResetDay();
    this.spentUsd += amountUsd;
  }

  isExhausted(): boolean {
    this.maybeResetDay();
    return this.spentUsd >= this.config.dailyLimitUsd;
  }

  status() {
    this.maybeResetDay();
    return {
      dailyLimitUsd: this.config.dailyLimitUsd,
      spentUsd: this.spentUsd,
      remainingUsd: Math.max(0, this.config.dailyLimitUsd - this.spentUsd),
    };
  }

  private maybeResetDay(): void {
    if (Date.now() - this.dayStart >= 86_400_000) {
      this.spentUsd = 0;
      this.dayStart = Date.now();
    }
  }
}

interface RateLimitConfig { windowMs: number; maxRequests: number; }

class RateLimiter {
  private windows = new Map<string, number[]>();

  constructor(private config: RateLimitConfig) {}

  isAllowed(ip: string): boolean {
    const now = Date.now();
    let timestamps = (this.windows.get(ip) || []).filter(t => t > now - this.config.windowMs);
    if (timestamps.length >= this.config.maxRequests) {
      this.windows.set(ip, timestamps);
      return false;
    }
    timestamps.push(now);
    this.windows.set(ip, timestamps);
    return true;
  }
}

export interface GovernanceState {
  circuitBreaker: CircuitBreaker;
  budget: BudgetTracker;
  rateLimiter: RateLimiter;
}

export function createGovernance(config: {
  circuitBreaker?: { threshold?: number; cooldownMs?: number };
  budget?: { dailyLimitUsd?: number };
  rateLimit?: { windowMs?: number; maxRequests?: number };
} = {}): GovernanceState {
  return {
    circuitBreaker: new CircuitBreaker({
      threshold: config.circuitBreaker?.threshold ?? 3,
      cooldownMs: config.circuitBreaker?.cooldownMs ?? 600_000,
    }),
    budget: new BudgetTracker({
      dailyLimitUsd: config.budget?.dailyLimitUsd ?? 50,
    }),
    rateLimiter: new RateLimiter({
      windowMs: config.rateLimit?.windowMs ?? 60_000,
      maxRequests: config.rateLimit?.maxRequests ?? 60,
    }),
  };
}

export function governanceMiddleware(state: GovernanceState) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (state.circuitBreaker.isOpen()) {
      res.status(503).json({ error: "circuit_breaker_open", retry_after_seconds: 60 });
      return;
    }
    if (state.budget.isExhausted()) {
      res.status(503).json({ error: "budget_exhausted" });
      return;
    }
    const ip = req.ip || req.socket.remoteAddress || "unknown";
    if (!state.rateLimiter.isAllowed(ip)) {
      res.status(429).json({ error: "rate_limited" });
      return;
    }
    next();
  };
}

export function recordUpstreamFailure(state: GovernanceState): void {
  state.circuitBreaker.recordFailure();
}

export function governanceStatus(state: GovernanceState) {
  return {
    circuitBreaker: state.circuitBreaker.status(),
    budget: state.budget.status(),
  };
}
