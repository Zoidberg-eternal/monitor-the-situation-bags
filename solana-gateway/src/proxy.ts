import type { Request, Response } from "express";
import type { GovernanceState } from "./governance.js";
import { recordUpstreamFailure } from "./governance.js";

export function createProxyHandler(
  upstreamUrl: string,
  governance: GovernanceState,
  networkLabel: string = "solana",
) {
  return async (req: Request, res: Response) => {
    const target = new URL(req.originalUrl, upstreamUrl);

    try {
      const upstream = await fetch(target.toString(), {
        method: req.method,
        headers: {
          Accept: "application/json",
          ...(req.method === "POST" ? { "Content-Type": "application/json" } : {}),
        },
        ...(req.method === "POST" && req.body ? { body: JSON.stringify(req.body) } : {}),
      });

      const body = await upstream.text();
      const contentType = upstream.headers.get("content-type");

      res.status(upstream.status);
      if (contentType) {
        res.setHeader("Content-Type", contentType);
      }

      if (contentType?.includes("application/json")) {
        try {
          const data = JSON.parse(body);
          data.payment_network = networkLabel;
          data.gateway = "solana-x402";
          res.json(data);
          return;
        } catch {
          // fallthrough
        }
      }

      res.send(body);
    } catch (err) {
      recordUpstreamFailure(governance);
      const message = err instanceof Error ? err.message : "Upstream request failed";
      res.status(502).json({
        error: "upstream_error",
        message,
        upstream: upstreamUrl,
      });
    }
  };
}
